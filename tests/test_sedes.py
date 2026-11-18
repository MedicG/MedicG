"""Establishments (sedes): patients per sede, staff limited to one sede, enforced on reads and writes."""
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
from medicg.entrypoint import ProductionHandler

PASSWORD = 'LocalTest-12345'


def main():
    tmp = tempfile.TemporaryDirectory()
    app.DB_DRIVER = 'sqlite'
    app.DB_PATH = Path(tmp.name) / 'sedes.sqlite3'
    app.ADMIN_EMAIL = 'admin@localhost.test'
    app.ADMIN_PASSWORD = PASSWORD
    app.init_db()
    with app.db() as conn:
        app.set_json_key(conn, 'config', {'nombre': 'Medic G', 'sedes': [{'id': 'gye', 'nombre': 'Guayaquil', 'principal': True}, {'id': 'balzar', 'nombre': 'Balzar'}]})
        app.set_json_key(conn, 'especialidades', [{'id': 1, 'nombre': 'Medicina General', 'estado': 'activo'}])
        app.set_json_key(conn, 'medicos', [{'id': 1, 'nombre': 'Dra. Gómez', 'esp': 'Medicina General', 'horario': 'Lun-Dom 07:00-19:00'}])
        app.set_json_key(conn, 'servicios', [{'id': 1, 'nombre': 'Consulta', 'precio': 20}])
        app.set_json_key(conn, 'pacientes', [{'id': 1, 'nombres': 'Ana', 'apellidos': 'Guayaquil', 'cedula': '0102', 'esp': 'Medicina General'},
                                             {'id': 2, 'nombres': 'Luis', 'apellidos': 'Balzar', 'cedula': '0103', 'esp': 'Medicina General', 'sede': 'balzar'}])
        app.set_json_key(conn, 'notas', {'1': [{'id': 1, 'fecha': '2026-11-01'}], '2': [{'id': 2, 'fecha': '2026-11-02'}]})
        app.set_json_key(conn, 'citas', [{'id': 1, 'pac': 1, 'med': 1, 'esp': 'Medicina General', 'fecha': '2026-11-20', 'hora': '09:00', 'estado': 'Pendiente'},
                                         {'id': 2, 'pac': 2, 'med': 1, 'esp': 'Medicina General', 'fecha': '2026-11-20', 'hora': '10:00', 'estado': 'Pendiente'}])
        app.set_json_key(conn, 'nextIds', {'pac': 3, 'cita': 3, 'user': 4})
        users = app.get_json_key(conn, 'users')
        for uid, email, extra in ((2, 'balzar@localhost.test', {'sede': 'balzar'}), (3, 'todas@localhost.test', {})):
            users.append({'id': uid, 'name': 'Recep', 'last': str(uid), 'email': email, 'rol': 'recepcion', 'estado': 'activo', 'emailVerified': True,
                          'passHash': app.hash_password(PASSWORD), 'permissions': app.clean_permissions(['dashboard', 'agenda', 'caja', 'pacientes', 'hce'], 'recepcion'), **extra})
        app.set_json_key(conn, 'users', users)

    class Quiet(ProductionHandler):
        def log_message(self, *args):
            pass
    server = app.ThreadingHTTPServer(('127.0.0.1', 0), Quiet)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = 'http://127.0.0.1:' + str(server.server_port)

    def call(token, path, payload=None):
        req = urllib.request.Request(base + path, data=None if payload is None else json.dumps(payload).encode(),
                                     headers={'Content-Type': 'application/json', **({'Authorization': 'Bearer ' + token} if token else {})})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def login(email):
        code, body = call('', '/api/login', {'email': email, 'password': PASSWORD})
        assert code == 200, body
        return body['token']
    admin, bz, todas = login('admin@localhost.test'), login('balzar@localhost.test'), login('todas@localhost.test')

    # reads: the Balzar receptionist only receives Balzar patients and their records
    data = call(bz, '/api/data')[1]['data']
    assert [p['id'] for p in data['pacientes']] == [2] and list(data['notas']) == ['2'] and [c['pac'] for c in data['citas']] == [2], data['citas']
    assert len(call(todas, '/api/data')[1]['data']['pacientes']) == 2 and len(call(admin, '/api/data')[1]['data']['pacientes']) == 2

    # writes: a new patient goes to Balzar and Guayaquil patients are preserved
    new = {'id': 3, 'nombres': 'Rosa', 'apellidos': 'Nueva', 'cedula': '0104', 'esp': 'Medicina General', 'sede': 'gye'}
    code, body = call(bz, '/api/data', {'key': 'pacientes', 'value': data['pacientes'] + [new], 'baseValue': data['pacientes']})
    assert code == 200, body
    with app.db() as conn:
        stored = {p['id']: p for p in app.get_json_key(conn, 'pacientes')}
    assert set(stored) == {1, 2, 3} and stored[3]['sede'] == 'balzar', stored
    with app.db() as conn:
        assert [p['id'] for p in app.get_json_key(conn, 'pacientes')] == [1, 2, 3], 'other sedes keep their position'
    # cannot edit or move patients of another sede
    full = call(admin, '/api/data')[1]['data']['pacientes']
    edited = [dict(p, tel='099') for p in full]
    assert call(bz, '/api/data', {'key': 'pacientes', 'value': edited, 'baseValue': full})[0] in (403, 409)
    mine = call(bz, '/api/data')[1]['data']['pacientes']
    moved = [dict(p, sede='gye') if p['id'] == 2 else p for p in mine]
    assert call(bz, '/api/data', {'key': 'pacientes', 'value': moved, 'baseValue': mine})[0] == 403
    # clinical documents, appointments and cash are checked per patient
    assert call(bz, '/api/clinical/docs', {'action': 'vitals_save', 'patientId': 1, 'peso': 60})[0] == 409
    assert call(bz, '/api/clinical/docs', {'action': 'vitals_save', 'patientId': 2, 'peso': 60})[0] == 200
    appt = {'pac': 1, 'med': 1, 'esp': 'Medicina General', 'tipo': 'Control', 'fecha': (datetime.date.today() + datetime.timedelta(days=3)).isoformat(),
            'hora': '11:00', 'motivo': 'x', 'estado': 'Pendiente', 'notif': 'Sin recordatorio'}
    code, body = call(bz, '/api/appointments', appt)
    assert code in (400, 409) and 'establecimiento' in body.get('error', ''), body
    call(bz, '/api/cash/open', {'montoApertura': 0})
    code, body = call(bz, '/api/cash/charge', {'requestId': 'req-sede-00000001', 'patientId': 1, 'items': [{'kind': 'servicio', 'id': 1, 'quantity': 1}], 'expectedTotal': 20, 'payments': []})
    assert code == 409 and 'establecimiento' in body['error'], body
    # users: the administrator assigns a valid sede
    code, body = call(admin, '/api/users', {'action': 'update', 'userId': 3, 'name': 'Recep', 'last': '3', 'email': 'todas@localhost.test', 'rol': 'recepcion', 'sede': 'quito'})
    assert code == 400, body
    code, body = call(admin, '/api/users', {'action': 'update', 'userId': 3, 'name': 'Recep', 'last': '3', 'email': 'todas@localhost.test', 'rol': 'recepcion', 'sede': 'gye',
                                            'permissions': ['dashboard', 'agenda', 'pacientes', 'hce']})
    assert code == 200 and body['user']['sede'] == 'gye', body
    got = call(todas, '/api/data')[1]['data']['pacientes']
    assert [p['id'] for p in got] == [1], ('patients without sede belong to the main sede', [(p['id'], p.get('sede')) for p in got])
    code, body = call(admin, '/api/users', {'name': 'Nuevo', 'last': 'B', 'email': 'nuevo@localhost.test', 'password': PASSWORD, 'rol': 'recepcion', 'sede': 'balzar'})
    assert code in (200, 201) and body['user']['sede'] == 'balzar', body
    server.shutdown(); server.server_close(); tmp.cleanup()
    print('PASS sedes: patients per establishment, staff limited to their sede on reads and writes, clinical docs, appointments, cash and users')


if __name__ == '__main__':
    main()
