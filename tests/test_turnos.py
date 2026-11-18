"""Turn system: numbering per area/sede/day, preferential first, calls, states, display screen with key."""
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
    app.DB_PATH = Path(tmp.name) / 'turnos.sqlite3'
    app.ADMIN_EMAIL = 'admin@localhost.test'
    app.ADMIN_PASSWORD = PASSWORD
    app.init_db()
    with app.db() as conn:
        app.set_json_key(conn, 'config', {'nombre': 'Medic G', 'sedes': [{'id': 'gye', 'nombre': 'Guayaquil', 'principal': True}, {'id': 'balzar', 'nombre': 'Balzar'}]})
        app.set_json_key(conn, 'pacientes', [{'id': 1, 'nombres': 'MARIA JOSE', 'apellidos': 'PEREZ LOOR', 'cedula': '0102'},
                                             {'id': 2, 'nombres': 'Luis', 'apellidos': 'Mora', 'cedula': '0103', 'sede': 'balzar'}])
        users = app.get_json_key(conn, 'users')
        users.append({'id': 2, 'name': 'Recep', 'last': 'Balzar', 'email': 'bz@localhost.test', 'rol': 'recepcion', 'estado': 'activo', 'emailVerified': True,
                      'passHash': app.hash_password(PASSWORD), 'permissions': app.clean_permissions(['agenda'], 'recepcion'), 'sede': 'balzar', 'sedeSolo': True})
        users.append({'id': 3, 'name': 'Sin', 'last': 'Permiso', 'email': 'np@localhost.test', 'rol': 'asistente', 'estado': 'activo', 'emailVerified': True,
                      'passHash': app.hash_password(PASSWORD), 'permissions': ['servicios']})
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
        return call('', '/api/login', {'email': email, 'password': PASSWORD})[1]['token']
    admin, bz, np_ = login('admin@localhost.test'), login('bz@localhost.test'), login('np@localhost.test')

    assert call(np_, '/api/turnos')[0] == 403
    state = call(admin, '/api/turnos')[1]
    assert state['sede'] == 'gye' and [a['letra'] for a in state['areas']] == ['C', 'L', 'K'] and state['turnos'] == []
    t1 = call(admin, '/api/turnos', {'action': 'crear', 'area': 'C', 'pacienteId': 1})[1]['turno']
    t2 = call(admin, '/api/turnos', {'action': 'crear', 'area': 'C', 'nombre': 'Walk in'})[1]['turno']
    t3 = call(admin, '/api/turnos', {'action': 'crear', 'area': 'C', 'prioridad': True, 'nombre': 'Adulto mayor'})[1]['turno']
    lab = call(admin, '/api/turnos', {'action': 'crear', 'area': 'L'})[1]['turno']
    assert [t1['codigo'], t2['codigo'], t3['codigo'], lab['codigo']] == ['C-001', 'C-002', 'C-003', 'L-001'] and t1['nombre'] == 'MARIA JOSE PEREZ LOOR'
    assert call(admin, '/api/turnos', {'action': 'crear', 'area': 'Z'})[0] == 409
    # Balzar numbers independently and only sees its own sede
    b1 = call(bz, '/api/turnos', {'action': 'crear', 'area': 'C'})[1]['turno']
    assert b1['codigo'] == 'C-001' and b1['sede'] == 'balzar'
    assert call(bz, '/api/turnos', {'action': 'crear', 'area': 'C', 'pacienteId': 1})[0] == 409, 'patient of another sede'
    assert call(bz, '/api/turnos?sede=gye')[0] == 403
    assert [t['codigo'] for t in call(bz, '/api/turnos')[1]['turnos']] == ['C-001']
    # calls: preferential first, then arrival order; destination required
    assert call(admin, '/api/turnos', {'action': 'llamar', 'area': 'C'})[0] == 409
    first = call(admin, '/api/turnos', {'action': 'llamar', 'area': 'C', 'destino': 'Consultorio 2'})[1]['turno']
    assert first['codigo'] == 'C-003' and first['estado'] == 'llamado' and first['llamadas'] == 1
    second = call(admin, '/api/turnos', {'action': 'llamar', 'areas': ['C', 'L'], 'destino': 'Consultorio 1'})[1]['turno']
    assert second['codigo'] == 'C-001'
    again = call(admin, '/api/turnos', {'action': 'llamar', 'id': second['id'], 'destino': 'Consultorio 1'})[1]['turno']
    assert again['llamadas'] == 2
    assert call(admin, '/api/turnos', {'action': 'estado', 'id': second['id'], 'estado': 'atendido'})[1]['turno']['estado'] == 'atendido'
    assert call(admin, '/api/turnos', {'action': 'llamar', 'id': second['id'], 'destino': 'X'})[0] == 409
    # display screen: needs the key (or a staff session); shows no names unless enabled
    assert call('', '/api/turnos/pantalla?sede=gye')[0] == 403
    code, cfg = call(admin, '/api/turnos', {'action': 'config', 'areas': [{'letra': 'C', 'nombre': 'Consulta'}, {'letra': 'L', 'nombre': 'Laboratorio'}, {'letra': 'P', 'nombre': 'Preferencial'}], 'mostrarNombre': False})
    key = cfg['turnos']['displayKey']
    assert code == 200 and len(key) > 16
    assert call(bz, '/api/turnos', {'action': 'config', 'areas': [{'letra': 'C', 'nombre': 'x'}]})[0] == 403
    code, screen = call('', f'/api/turnos/pantalla?sede=gye&k={key}')
    assert code == 200 and screen['actual']['codigo'] == 'C-001' and screen['actual']['destino'] == 'Consultorio 1' and screen['actual']['nombre'] == ''
    assert [r['codigo'] for r in screen['recientes']] == ['C-003'] and screen['espera'] == {'C': 1, 'L': 1} and screen['sedeNombre'] == 'Guayaquil'
    assert call('', f'/api/turnos/pantalla?sede=gye&k=wrong')[0] == 403
    call(admin, '/api/turnos', {'action': 'config', 'areas': [{'letra': 'C', 'nombre': 'Consulta'}], 'mostrarNombre': True})
    assert call('', f'/api/turnos/pantalla?sede=gye&k={key}')[1]['actual']['nombre'] == 'Maria P.'
    new_key = call(admin, '/api/turnos', {'action': 'config', 'areas': [{'letra': 'C', 'nombre': 'Consulta'}], 'nuevaClave': True})[1]['turnos']['displayKey']
    assert new_key != key and call('', f'/api/turnos/pantalla?sede=gye&k={key}')[0] == 403
    assert call('', f'/api/turnos/pantalla?sede=balzar&k={new_key}')[1]['actual'] is None
    # Calling the next turn to the same room closes the one attended there.
    w = call(admin, '/api/turnos', {'action': 'crear', 'area': 'C'})[1]['turno']
    call(admin, '/api/turnos', {'action': 'llamar', 'areas': ['C', 'L'], 'destino': 'Consultorio 2'})
    rows = {t['codigo']: t for t in call(admin, '/api/turnos')[1]['turnos']}
    assert rows['C-003']['estado'] == 'atendido' and rows['C-002']['estado'] == 'llamado' and rows['C-002']['destino'] == 'Consultorio 2', rows
    assert call('', '/api/turnos/pantalla?sede=gye&k=' + new_key)[1]['logo'] == ''
    server.shutdown(); server.server_close(); tmp.cleanup()
    print('PASS turnos: numbering per area/sede/day, preferential first, recall and states, sede limits, display screen with private key and optional short names')


if __name__ == '__main__':
    main()
