"""Appointment reminders: plan parsing, due windows, e-mail, WhatsApp Business (mocked),
manual wa.me links, no duplicates, private settings, cron and patient double booking."""
import datetime
import json
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import medicg_app as app
import medicg.mailer as mailer
import medicg.reminders as reminders
from medicg.entrypoint import ProductionHandler

PASSWORD = 'LocalTest-12345'
SENT_MAIL, SENT_WA = [], []


def main():
    mailer.send = lambda to, subject, text, html, attachments=None, config=None, conn=None: (SENT_MAIL.append((to, subject, text)) or True, '')
    reminders.send_whatsapp_cloud = lambda cfg, phone, params: (SENT_WA.append((phone, params)) or True, 'wamid.TEST')
    # plan parsing
    assert reminders.plan('WhatsApp + Correo (24h antes)') == ({'whatsapp', 'email'}, [24])
    assert reminders.plan('Solo WhatsApp (2h antes)') == ({'whatsapp'}, [2])
    assert reminders.plan('WhatsApp + Correo (24h y 2h antes)')[1] == [24, 2]
    assert reminders.plan('Sin recordatorio') == (set(), [])
    assert reminders.phone_e164('099 123 4567') == '593991234567' and reminders.phone_e164('+593 99 123 4567') == '593991234567' and reminders.phone_e164('12') == ''

    # 24h window: the 07:00 daily run must cover an appointment at 15:00 next day (32 h ahead)
    now_ = datetime.datetime(2026, 11, 2, 7, 0, tzinfo=reminders.TZ)
    assert reminders.due({'estado': 'Confirmada', 'fecha': '2026-11-03', 'hora': '15:00', 'notif': 'Solo correo (24h antes)'}, now_) == [('email', '24h')]
    assert reminders.due({'estado': 'Confirmada', 'fecha': '2026-11-04', 'hora': '15:00', 'notif': 'Solo correo (24h antes)'}, now_) == []
    assert reminders.due({'estado': 'Cancelada', 'fecha': '2026-11-03', 'hora': '15:00', 'notif': 'Solo correo (24h antes)'}, now_) == []
    # relative day wording
    today_ = datetime.datetime.now(reminders.TZ).date()
    txt = reminders.message({'fecha': today_.isoformat(), 'hora': '18:00'}, {'nombres': 'ana'}, {}, {}, '24h')[0]
    assert 'cita de hoy' in txt and 'mañana' not in txt.split('\n')[0], txt
    txt = reminders.message({'fecha': (today_ + datetime.timedelta(days=1)).isoformat(), 'hora': '09:00'}, {'nombres': 'ana'}, {}, {}, '24h')[0]
    assert 'cita de mañana' in txt

    temporary = tempfile.TemporaryDirectory()
    app.DB_DRIVER = 'sqlite'
    app.DB_PATH = Path(temporary.name) / 'reminders.sqlite3'
    app.ADMIN_EMAIL = 'admin@localhost.test'
    app.ADMIN_PASSWORD = PASSWORD
    app.init_db()
    tz = reminders.TZ
    soon = datetime.datetime.now(tz) + datetime.timedelta(hours=20)
    soon2 = datetime.datetime.now(tz) + datetime.timedelta(hours=1, minutes=30)
    far = datetime.datetime.now(tz) + datetime.timedelta(days=5)
    with app.db() as conn:
        app.set_json_key(conn, 'config', {'nombre': 'Centro Prueba', 'dir': 'Av. Siempre Viva 123', 'tel': '042000000'})
        app.set_json_key(conn, 'pacientes', [{'id': 1, 'nombres': 'ana maria', 'apellidos': 'Paz', 'email': 'ana@localhost.test', 'tel': '0991234567'},
                                             {'id': 2, 'nombres': 'Luis', 'apellidos': 'Mora', 'email': '', 'tel': ''}])
        app.set_json_key(conn, 'medicos', [{'id': 1, 'nombre': 'Dra. Gómez', 'esp': 'Medicina General', 'horario': ''}])
        app.set_json_key(conn, 'citas', [
            {'id': 1, 'pac': 1, 'med': 1, 'esp': 'Medicina General', 'fecha': soon.date().isoformat(), 'hora': soon.strftime('%H:%M'), 'estado': 'Confirmada', 'notif': 'WhatsApp + Correo (24h antes)'},
            {'id': 2, 'pac': 2, 'med': 1, 'esp': 'Medicina General', 'fecha': soon.date().isoformat(), 'hora': soon.strftime('%H:%M'), 'estado': 'Confirmada', 'notif': 'Solo correo'},
            {'id': 3, 'pac': 1, 'med': 1, 'esp': 'Medicina General', 'fecha': far.date().isoformat(), 'hora': '09:00', 'estado': 'Confirmada', 'notif': 'WhatsApp + Correo (24h antes)'},
            {'id': 4, 'pac': 1, 'med': 1, 'esp': 'Medicina General', 'fecha': soon.date().isoformat(), 'hora': soon.strftime('%H:%M'), 'estado': 'Cancelada', 'notif': 'WhatsApp + Correo (24h antes)'},
            {'id': 5, 'pac': 1, 'med': 1, 'esp': 'Medicina General', 'fecha': soon2.date().isoformat(), 'hora': soon2.strftime('%H:%M'), 'estado': 'Pendiente', 'notif': 'WhatsApp + Correo (24h y 2h antes)'},
        ])
        users = app.get_json_key(conn, 'users')
        users.append({'id': 2, 'name': 'Rita', 'last': 'R', 'email': 'recep@localhost.test', 'rol': 'recepcion', 'estado': 'activo', 'emailVerified': True,
                      'passHash': app.hash_password(PASSWORD), 'permissions': app.clean_permissions(None, 'recepcion')})
        app.set_json_key(conn, 'users', users)
        ids = app.get_json_key(conn, 'nextIds'); ids['user'] = 3; ids['cita'] = 10; app.set_json_key(conn, 'nextIds', ids)

    class Quiet(ProductionHandler):
        def log_message(self, *args):
            pass
    server = app.ThreadingHTTPServer(('127.0.0.1', 0), Quiet)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = 'http://127.0.0.1:' + str(server.server_port)

    def call(token, path, payload=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        req = urllib.request.Request(base + path, data=None if payload is None else json.dumps(payload).encode(), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())
    admin = call('', '/api/login', {'email': app.ADMIN_EMAIL, 'password': PASSWORD})[1]['token']
    recep = call('', '/api/login', {'email': 'recep@localhost.test', 'password': PASSWORD})[1]['token']

    # manual WhatsApp mode: e-mail goes out automatically, WhatsApp is prepared as a link
    code, body = call(recep, '/api/reminders/run', {})
    assert code == 200 and body['sent'] == 2, body          # cita 1 e-mail + cita 5 e-mail (2h window)
    assert {m[0] for m in SENT_MAIL} == {'ana@localhost.test'} and 'Ana' in SENT_MAIL[0][2] and 'Av. Siempre Viva' in SENT_MAIL[0][2]
    assert not SENT_WA
    assert call(recep, '/api/reminders/run', {})[1].get('throttled')          # rate limited
    call(admin, '/api/reminders/run', {'force': True})
    assert len(SENT_MAIL) == 2                                                 # no duplicates
    code, body = call(recep, '/api/reminders/send', {'citaId': 1, 'channels': ['whatsapp', 'email'], 'kind': 'manual'})
    wa = body['results']['whatsapp']
    assert wa['status'] == 'pending_manual' and wa['waLink'].startswith('https://wa.me/593991234567?text='), body
    assert body['results']['email']['status'] == 'sent'
    assert call(recep, '/api/reminders/mark', {'citaId': 1, 'kind': 'manual'})[0] == 200
    code, body = call(recep, '/api/reminders/send', {'citaId': 2, 'channels': ['email', 'whatsapp']})
    assert body['results']['email']['status'] == 'skipped' and body['results']['whatsapp']['status'] == 'skipped', body
    status = call(recep, '/api/reminders/status?ids=1,2,5')[1]['status']
    assert any(x['status'] == 'manual' and x['channel'] == 'whatsapp' for x in status['1']) and any(x['status'] == 'skipped' for x in status['2'])

    # WhatsApp Business settings are private and enable automatic sending
    assert call(recep, '/api/reminders/settings', {'whatsappMode': 'manual'})[0] == 409
    assert call(admin, '/api/reminders/settings', {'whatsappMode': 'cloud', 'phoneNumberId': 'abc'})[0] == 409
    code, body = call(admin, '/api/reminders/settings', {'whatsappMode': 'cloud', 'phoneNumberId': '1234567890', 'token': 'SECRET-TOKEN', 'templateName': 'recordatorio_cita', 'templateLang': 'es'})
    assert code == 200 and body['settings']['whatsappAutomatic'] and 'token' not in body['settings']
    assert 'SECRET-TOKEN' not in json.dumps(call(admin, '/api/data')[1]) and 'remindersPrivate' not in call(admin, '/api/data')[1]['data']
    call(admin, '/api/reminders/run', {'force': True})
    assert sorted(p for p, _ in SENT_WA) == ['593991234567', '593991234567'], SENT_WA   # cita 1 (24h) + cita 5 (2h)
    assert SENT_WA[0][1]['paciente'] == 'Ana' and SENT_WA[0][1]['centro'] == 'Centro Prueba'
    call(admin, '/api/reminders/run', {'force': True})
    assert len(SENT_WA) == 2
    # daily cron endpoint works without a session (rate limited, idempotent)
    assert call('', '/api/reminders/cron')[0] == 200

    # a run interrupted after reserving a message never sends it twice
    with app.db() as conn:
        citas = app.get_json_key(conn, 'citas')
        citas.append({'id': 9, 'pac': 1, 'med': 1, 'esp': 'Medicina General', 'fecha': soon.date().isoformat(), 'hora': soon.strftime('%H:%M'), 'estado': 'Confirmada', 'notif': 'Solo correo (24h antes)'})
        app.set_json_key(conn, 'citas', citas)
        reminders.log(conn, 9, 'email', '24h', f"{soon.date().isoformat()} {soon.strftime('%H:%M')}", 'sending', 'Reservado para envío')
    before = len(SENT_MAIL)
    call(admin, '/api/reminders/run', {'force': True})
    assert len(SENT_MAIL) == before, 'reserved message must not be resent'
    # time budget: unattempted reservations are released for the next run
    original_budget, original_execute = reminders.TIME_BUDGET_SECONDS, reminders.execute
    reminders.TIME_BUDGET_SECONDS = -1
    with app.db() as conn:
        citas = app.get_json_key(conn, 'citas')
        citas.append({'id': 10, 'pac': 1, 'med': 1, 'esp': 'Medicina General', 'fecha': (soon + datetime.timedelta(minutes=5)).date().isoformat(), 'hora': (soon + datetime.timedelta(minutes=5)).strftime('%H:%M'), 'estado': 'Confirmada', 'notif': 'Solo correo (24h antes)'})
        app.set_json_key(conn, 'citas', citas)
    body = call(admin, '/api/reminders/run', {'force': True})[1]
    assert body.get('more') and body['sent'] == 0, body
    with app.db(read_only=True) as conn:
        assert conn.execute("select count(*) as n from reminder_log where cita_id = '10'").fetchone()['n'] == 0
    reminders.TIME_BUDGET_SECONDS = original_budget
    body = call(admin, '/api/reminders/run', {'force': True})[1]
    assert body['sent'] >= 1 and any(m[0] == 'ana@localhost.test' for m in SENT_MAIL[before:]), body

    # patient double booking is rejected
    day = datetime.date.today() + datetime.timedelta(days=7)
    day += datetime.timedelta(days=(0 - day.weekday()) % 7)
    with app.db() as conn:
        app.set_json_key(conn, 'medicos', [{'id': 1, 'nombre': 'Dra. Gómez', 'esp': 'Medicina General'}, {'id': 2, 'nombre': 'Dr. Ruiz', 'esp': 'Medicina General'}])
    payload = {'pac': 1, 'med': 1, 'esp': 'Medicina General', 'fecha': day.isoformat(), 'hora': '09:00', 'estado': 'Confirmada', 'tipo': 'Control', 'motivo': 'x', 'notif': 'Solo correo'}
    assert call(admin, '/api/appointments', payload)[0] == 200
    code, body = call(admin, '/api/appointments', dict(payload, med=2))
    assert code == 409 and 'ya tiene una cita' in body['error'], body

    server.shutdown(); server.server_close(); temporary.cleanup()
    print('PASS reminder plans, due windows (24h/2h), e-mail, WhatsApp Business and manual links, no duplicates, rate limit, private settings, cron and patient double booking')


if __name__ == '__main__':
    main()
