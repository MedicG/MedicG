"""Daily cash close by reception, superadmin doctors, editable vital signs,
medical certificates and lab orders. Temporary SQLite only."""
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
    temporary = tempfile.TemporaryDirectory()
    app.DB_DRIVER = 'sqlite'
    app.DB_PATH = Path(temporary.name) / 'features.sqlite3'
    app.ADMIN_EMAIL = 'admin@localhost.test'
    app.ADMIN_PASSWORD = PASSWORD
    app.init_db()
    with app.db() as conn:
        app.set_json_key(conn, 'pacientes', [{'id': 1, 'nombres': 'Ana', 'apellidos': 'Paz', 'cedula': '0102', 'esp': 'Medicina General'},
                                             {'id': 2, 'nombres': 'Luis', 'apellidos': 'Mora', 'cedula': '0103', 'esp': 'Cardiología'}])
        app.set_json_key(conn, 'medicos', [{'id': 1, 'nombre': 'Dra. Gómez', 'esp': 'Medicina General', 'cedula': '1700', 'sen': 'REG-1'},
                                           {'id': 2, 'nombre': 'Dr. Ruiz', 'esp': 'Cardiología'}])
        app.set_json_key(conn, 'examenes', [{'id': 10, 'nombre': 'Hemograma', 'categoria': 'Hematología', 'precio': 8},
                                            {'id': 11, 'nombre': 'Glucosa', 'categoria': 'Química', 'precio': 3}])
        app.set_json_key(conn, 'servicios', [{'id': 1, 'nombre': 'Consulta', 'precio': 20}])
        app.set_json_key(conn, 'notas', {'1': [{'id': 555, 'fecha': '2026-10-01', 'pa': '150/90', 'fc': '90'}]})
        users = app.get_json_key(conn, 'users')
        for uid, email, rol, extra in ((2, 'recep@localhost.test', 'recepcion', {}), (3, 'medgen@localhost.test', 'medico', {'medicoId': 1}),
                                       (4, 'cardio@localhost.test', 'medico', {'medicoId': 2}), (5, 'asis@localhost.test', 'asistente', {})):
            users.append({'id': uid, 'name': rol, 'last': 'Test', 'email': email, 'rol': rol, 'estado': 'activo', 'emailVerified': True,
                          'passHash': app.hash_password(PASSWORD), 'permissions': app.clean_permissions(['agenda', 'hce'] if rol == 'asistente' else None, rol), **extra})
        app.set_json_key(conn, 'users', users)

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

    def login(email):
        code, body = call('', '/api/login', {'email': email, 'password': PASSWORD})
        assert code == 200, body
        return body['token']

    admin, recep, medgen, cardio, asis = (login(e) for e in ('admin@localhost.test', 'recep@localhost.test', 'medgen@localhost.test', 'cardio@localhost.test', 'asis@localhost.test'))

    # ---- daily cash close by reception
    assert call(medgen, '/api/cash/open', {})[0] == 403
    code, body = call(recep, '/api/cash/open', {'montoApertura': 20})
    assert code == 200 and body['box']['montoApertura'] == 20, body
    assert call(recep, '/api/cash/open', {})[0] == 409  # only one open box
    box_id = body['box']['id']
    code, body = call(recep, '/api/cash/charge', {'requestId': 'req-feature-0000001', 'patientId': 1, 'items': [{'kind': 'servicio', 'id': 1, 'quantity': 1}],
                                                  'expectedTotal': 20, 'payments': [{'method': 'Efectivo', 'amount': 15}, {'method': 'Transferencia', 'amount': 5}]})
    assert code == 200, body
    assert call(recep, '/api/cash/close', {'boxId': box_id, 'expectedTotal': 15, 'efectivoContado': 35})[0] == 409  # stale total
    code, body = call(recep, '/api/cash/close', {'boxId': box_id, 'expectedTotal': 20, 'efectivoContado': 30})
    assert code == 409 and 'diferencia' in body['error'], body  # difference needs a reason
    code, body = call(recep, '/api/cash/close', {'boxId': box_id, 'expectedTotal': 20, 'efectivoContado': 30, 'observaciones': 'Faltan 5 dólares de vuelto'})
    assert code == 200, body
    closing = body['box']['cierre']
    assert closing['efectivoEsperado'] == 35 and closing['diferencia'] == -5 and closing['totales']['Transferencia'] == 5, closing
    boxes = call(admin, '/api/data')[1]['data']['cajas']
    tampered = json.loads(json.dumps(boxes)); tampered[0]['cierre']['diferencia'] = 0
    assert call(admin, '/api/data', {'key': 'cajas', 'value': tampered, 'baseValue': boxes})[0] == 409

    # ---- superadmin doctor
    code, body = call(admin, '/api/users', {'name': 'Super', 'last': 'Doc', 'email': 'super@localhost.test', 'password': PASSWORD, 'rol': 'medico_superadmin', 'medicoId': 1})
    assert code == 200 and body['user']['rol'] == 'admin' and body['user']['medicoId'] == 1 and body['user']['superadminMedico'], body
    superdoc = login('super@localhost.test')
    r = call(superdoc, '/api/patients/trash'); assert r[0] == 200, r  # admin-only route works
    code, body = call(admin, '/api/users', {'action': 'update', 'userId': body['user']['id'], 'name': 'Super', 'last': 'Doc', 'email': 'super@localhost.test', 'rol': 'medico', 'medicoId': 1})
    assert code == 200 and body['user']['rol'] == 'medico' and not body['user']['superadminMedico'], body
    call(admin, '/api/users', {'action': 'update', 'userId': body['user']['id'], 'name': 'Super', 'last': 'Doc', 'email': 'super@localhost.test', 'rol': 'medico_superadmin', 'medicoId': 1})
    superdoc = login('super@localhost.test')
    from medicg.telehealth import permitted
    assert permitted({'rol': 'admin', 'medicoId': 1}, {'med': 1}) and not permitted({'rol': 'admin'}, {'med': 1})

    # ---- vital signs
    today = datetime.date.today().isoformat()
    code, body = call(asis, '/api/clinical/docs', {'action': 'vitals_save', 'patientId': 1, 'pa': '120/80', 'peso': 70, 'talla': 170, 'fecha': today, 'hora': '08:00'})
    assert code == 200 and body['records'][0]['valores']['imc'] == 24.2, body
    rid = body['records'][0]['id']
    assert call(asis, '/api/clinical/docs', {'action': 'vitals_save', 'patientId': 1, 'id': rid, 'pa': '130/80', 'motivo': 'x'})[0] == 409  # not a doctor
    assert call(medgen, '/api/clinical/docs', {'action': 'vitals_save', 'patientId': 1, 'id': rid, 'pa': '130/80'})[0] == 409  # reason required
    assert call(medgen, '/api/clinical/docs', {'action': 'vitals_save', 'patientId': 1, 'pa': '80/120'})[0] == 409  # invalid
    code, body = call(medgen, '/api/clinical/docs', {'action': 'vitals_save', 'patientId': 1, 'id': rid, 'pa': '130/85', 'peso': 70, 'talla': 170, 'motivo': 'Error de digitación'})
    rec = body['records'][0]
    assert code == 200 and rec['valores']['pa'] == '130/85' and rec['historial'][0]['valores']['pa'] == '120/80', body
    code, body = call(medgen, '/api/clinical/docs', {'action': 'note_vitals', 'patientId': 1, 'noteId': 555, 'pa': '140/90', 'fc': 88, 'motivo': 'Toma repetida'})
    assert code == 200 and body['records'][0]['pa'] == '140/90' and body['records'][0]['signosHistorial'][0]['valores']['pa'] == '150/90', body
    assert call(cardio, '/api/clinical/docs', {'action': 'vitals_save', 'patientId': 1, 'pa': '120/80'})[0] == 409  # other specialty
    assert call(superdoc, '/api/clinical/docs', {'action': 'vitals_save', 'patientId': 2, 'id': 'missing', 'pa': '120/80', 'motivo': 'x'})[0] == 409

    # ---- certificates
    code, body = call(medgen, '/api/clinical/docs', {'action': 'certificate_create', 'patientId': 1, 'tipo': 'Reposo médico', 'diagnostico': 'Faringitis', 'cie10': 'j02.9', 'diasReposo': 3, 'desde': today})
    cert = body['records'][0]
    assert code == 200 and cert['numero'] == 'CERT-000001' and cert['cie10'] == 'J02.9' and cert['medico']['registro'] == 'REG-1', body
    assert (datetime.date.fromisoformat(cert['reposo']['hasta']) - datetime.date.fromisoformat(cert['reposo']['desde'])).days == 2
    assert call(medgen, '/api/clinical/docs', {'action': 'certificate_create', 'patientId': 1, 'tipo': 'Reposo médico', 'diagnostico': 'x', 'diasReposo': 0})[0] == 409
    assert call(recep, '/api/clinical/docs', {'action': 'certificate_create', 'patientId': 1, 'tipo': 'Asistencia a consulta'})[0] == 409
    assert call(asis, '/api/clinical/docs', {'action': 'certificate_create', 'patientId': 1, 'tipo': 'Asistencia a consulta'})[0] == 409
    code, body = call(admin, '/api/clinical/docs', {'action': 'certificate_create', 'patientId': 2, 'tipo': 'Asistencia a consulta', 'doctorId': 2})
    assert code == 200 and body['records'][0]['medico']['nombre'] == 'Dr. Ruiz', body
    assert call(superdoc, '/api/clinical/docs', {'action': 'certificate_create', 'patientId': 1, 'tipo': 'Certificado de salud', 'contenido': 'Apto'})[1]['records'][0]['medico']['id'] == 1
    assert call(cardio, '/api/clinical/docs', {'action': 'certificate_void', 'patientId': 1, 'id': cert['id'], 'motivo': 'x'})[0] == 409
    code, body = call(medgen, '/api/clinical/docs', {'action': 'certificate_void', 'patientId': 1, 'id': cert['id'], 'motivo': 'Fecha errónea'})
    assert code == 200 and next(c for c in body['records'] if c['id'] == cert['id'])['estado'] == 'Anulado'

    # ---- reception issues certificates requested by a doctor (no access to the clinical record)
    code, body = call(recep, '/api/clinical/docs', {'action': 'certificate_create', 'patientId': 2, 'doctorId': 2, 'tipo': 'Reposo médico', 'diagnostico': 'Lumbalgia', 'diasReposo': 2, 'domicilio': 'Cdla. Martha de Roldós Mz 215', 'empresa': 'Comercial XYZ S.A.', 'cargo': 'Bodeguero'})
    assert code == 200, body
    rcert = body['records'][0]
    assert rcert['medico']['id'] == 2 and rcert['emitidoPorRol'] == 'recepcion' and rcert['reposo']['dias'] == 2, rcert
    assert (rcert['domicilio'], rcert['empresa'], rcert['cargo']) == ('Cdla. Martha de Roldós Mz 215', 'Comercial XYZ S.A.', 'Bodeguero'), rcert
    code, body = call(recep, '/api/clinical/docs', {'action': 'certificate_list', 'patientId': 2})
    assert code == 200 and body['records'][0]['id'] == rcert['id'], body
    for action in ('vitals_save', 'lab_order_create', 'note_vitals'):
        assert call(recep, '/api/clinical/docs', {'action': action, 'patientId': 2, 'examenes': [{'id': 10}]})[0] == 409, action
    other = call(admin, '/api/clinical/docs', {'action': 'certificate_create', 'patientId': 2, 'tipo': 'Asistencia a consulta', 'doctorId': 2})[1]['records'][0]
    assert call(recep, '/api/clinical/docs', {'action': 'certificate_void', 'patientId': 2, 'id': other['id'], 'motivo': 'x'})[0] == 409
    code, body = call(recep, '/api/clinical/docs', {'action': 'certificate_void', 'patientId': 2, 'id': rcert['id'], 'motivo': 'Días errados'})
    assert code == 200 and next(c for c in body['records'] if c['id'] == rcert['id'])['estado'] == 'Anulado'
    code, data = call(recep, '/api/data')
    assert code == 200 and not data.get('certificados') and not data.get('notas'), 'reception must not receive clinical data'
    assert 'certificados' in app.clean_permissions(['agenda'], 'recepcion')

    # ---- reception creates exam orders requested by a doctor
    assert call(recep, '/api/clinical/docs', {'action': 'lab_order_create', 'patientId': 2, 'examenes': [{'id': 10}]})[0] == 409  # doctor required
    code, body = call(recep, '/api/clinical/docs', {'action': 'lab_order_create', 'patientId': 2, 'doctorId': 2, 'examenes': [{'id': 10}, {'nombre': 'TSH'}], 'prioridad': 'Urgente'})
    assert code == 200, body
    rorder = body['records'][0]
    assert rorder['medico']['id'] == 2 and rorder['creadoPorRol'] == 'recepcion' and len(rorder['examenes']) == 2, rorder
    code, body = call(recep, '/api/clinical/docs', {'action': 'lab_order_list', 'patientId': 2})
    assert code == 200 and body['records'][0]['id'] == rorder['id']
    assert call(recep, '/api/clinical/docs', {'action': 'lab_order_status', 'patientId': 2, 'id': rorder['id'], 'estado': 'Muestra tomada'})[0] == 200
    doc_order = call(cardio, '/api/clinical/docs', {'action': 'lab_order_create', 'patientId': 2, 'examenes': [{'id': 11}]})[1]['records'][0]
    assert call(recep, '/api/clinical/docs', {'action': 'lab_order_status', 'patientId': 2, 'id': doc_order['id'], 'estado': 'Anulada', 'motivo': 'x'})[0] == 409
    assert call(recep, '/api/clinical/docs', {'action': 'lab_order_status', 'patientId': 2, 'id': rorder['id'], 'estado': 'Anulada', 'motivo': 'Duplicada'})[0] == 200
    assert 'ordenes' in app.clean_permissions(['agenda'], 'recepcion')
    code, data = call(recep, '/api/data')
    assert not data.get('ordenesLab'), 'reception must not receive lab orders in bulk'

    # ---- lab orders
    code, body = call(medgen, '/api/clinical/docs', {'action': 'lab_order_create', 'patientId': 1, 'examenes': [{'id': 10}, {'id': 11}, {'nombre': 'Perfil tiroideo'}, {'id': 10}],
                                                      'diagnostico': 'Control', 'prioridad': 'Urgente', 'indicaciones': 'Ayuno 8 horas'})
    order = body['records'][0]
    assert code == 200 and order['numero'].startswith('LAB-') and [e['nombre'] for e in order['examenes']] == ['Hemograma', 'Glucosa', 'Perfil tiroideo'], body
    assert call(medgen, '/api/clinical/docs', {'action': 'lab_order_create', 'patientId': 1, 'examenes': [{'id': 99}]})[0] == 409
    assert call(medgen, '/api/clinical/docs', {'action': 'lab_order_create', 'patientId': 1, 'examenes': []})[0] == 409
    code, body = call(asis, '/api/clinical/docs', {'action': 'lab_order_status', 'patientId': 1, 'id': order['id'], 'estado': 'Muestra tomada'})
    assert code == 200 and body['records'][0]['estado'] == 'Muestra tomada'
    assert call(asis, '/api/clinical/docs', {'action': 'lab_order_status', 'patientId': 1, 'id': order['id'], 'estado': 'Anulada', 'motivo': 'x'})[0] == 409
    assert call(medgen, '/api/clinical/docs', {'action': 'lab_order_status', 'patientId': 1, 'id': order['id'], 'estado': 'Anulada'})[0] == 409

    # ---- visibility and generic-save protection
    recep_data = call(recep, '/api/data')[1]['data']
    assert recep_data['certificados'] == {} and recep_data['ordenesLab'] == {} and recep_data['signosVitales'] == {}
    cardio_data = call(cardio, '/api/data')[1]['data']
    assert '1' not in cardio_data['certificados'] and '2' in cardio_data['certificados']
    assert call(admin, '/api/data', {'key': 'certificados', 'value': {}, 'baseValue': {}})[0] == 403

    server.shutdown(); server.server_close(); temporary.cleanup()
    print('PASS daily cash close by reception with cash count, immutable closings, superadmin doctor, editable vitals with history, HCU vitals correction, certificates, lab orders, scope and permissions')


if __name__ == '__main__':
    main()
