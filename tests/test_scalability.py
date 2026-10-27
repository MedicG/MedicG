"""Scalability regressions: record-level merge, compact deltas, clinical files
outside the JSON, light invoice payloads, login throttling, gzip and schema gating.
Uses a temporary SQLite database only."""
import gzip
import json
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import medicg_app as app
from medicg.entrypoint import ProductionHandler

PNG = "data:image/png;base64," + "A" * 5000


def main():
    temporary = tempfile.TemporaryDirectory()
    app.DB_DRIVER = 'sqlite'
    app.DB_PATH = Path(temporary.name) / 'scale.sqlite3'
    app.ADMIN_EMAIL = 'admin@localhost.test'
    app.ADMIN_PASSWORD = 'LocalTest-12345'
    # Legacy data: files embedded inside the JSON aggregate.
    with app.db() as conn:
        conn.execute("create table if not exists app_data(key text primary key, value text not null, updated_at text not null)")
        app.set_json_key(conn, 'archivosClinicos', {'1': [{'id': 11, 'nombre': 'rx.png', 'mime': 'image/png', 'dataUrl': PNG}]})
    app.init_db()
    with app.db(read_only=True) as conn:
        stored = app.get_json_key(conn, 'archivosClinicos')
        assert 'dataUrl' not in json.dumps(stored) and stored['1'][0]['hasFile'] is True
        assert conn.execute("select count(*) as n from clinical_files").fetchone()['n'] == 1
    started = time.time(); app.init_db(); assert time.time() - started < 0.5  # schema gate: no rewrite
    with app.db() as conn:
        app.set_json_key(conn, 'pacientes', [{'id': 1, 'nombres': 'Ana', 'tel': '1'}, {'id': 2, 'nombres': 'Luis', 'tel': '2'}])
        app.set_json_key(conn, 'facturas', [{'id': '001-001-000000001', 'pac': 1, 'total': 10, 'xml': '<x/>' * 500, 'signedXml': '<s/>'}])

    class Quiet(ProductionHandler):
        def log_message(self, *args):
            pass
    server = app.ThreadingHTTPServer(('127.0.0.1', 0), Quiet)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    state = {'token': ''}

    def request(path, payload=None, headers=None, raw=False):
        h = {'Content-Type': 'application/json', **(headers or {})}
        if state['token']:
            h['Authorization'] = 'Bearer ' + state['token']
        req = urllib.request.Request(base + path, data=None if payload is None else json.dumps(payload).encode(), headers=h)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                body = r.read()
                if raw:
                    return r.status, r.headers, body
                return r.status, json.loads(body)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    code, body = request('/api/login', {'email': app.ADMIN_EMAIL, 'password': app.ADMIN_PASSWORD})
    assert code == 200, body
    state['token'] = body['token']
    data = request('/api/data')[1]['data']
    assert 'xml' not in data['facturas'][0] and 'dataUrl' not in json.dumps(data['archivosClinicos'])

    # Two users edit different patients from the same stale copy: both saves succeed.
    snapshot = data['pacientes']
    a = json.loads(json.dumps(snapshot)); a[0]['tel'] = '111'
    b = json.loads(json.dumps(snapshot)); b[1]['tel'] = '222'
    assert request('/api/data', {'key': 'pacientes', 'value': a, 'baseValue': snapshot})[0] == 200
    assert request('/api/data', {'key': 'pacientes', 'value': b, 'baseValue': snapshot})[0] == 200
    merged = {p['id']: p['tel'] for p in request('/api/data')[1]['data']['pacientes']}
    assert merged == {1: '111', 2: '222'}, merged
    # Same record edited from a stale copy: conflict, nothing overwritten.
    c = json.loads(json.dumps(snapshot)); c[0]['tel'] = '999'
    code, body = request('/api/data', {'key': 'pacientes', 'value': c, 'baseValue': snapshot})
    assert code == 409 and body['conflicts'] == ['1'], body

    # Compact delta (what the browser now sends): add a patient, positions preserved.
    current = request('/api/data')[1]['data']['pacientes']
    delta = {'type': 'list', 'upsert': [{'id': 3, 'nombres': 'Nuevo'}], 'remove': [], 'base': {'3': None}, 'positions': {'3': 0}}
    assert request('/api/data', {'key': 'pacientes', 'delta': delta})[0] == 200
    assert request('/api/data')[1]['data']['pacientes'][0]['id'] == 3
    # A new record reusing an existing id with other content is rejected.
    clash = {'type': 'list', 'upsert': [{'id': 1, 'nombres': 'Otro'}], 'remove': [], 'base': {'1': None}}
    assert request('/api/data', {'key': 'pacientes', 'delta': clash})[0] == 409
    # Removing patients still requires the trash flow.
    rm = {'type': 'list', 'upsert': [], 'remove': ['2'], 'base': {'2': next(p for p in current if p['id'] == 2)}}
    assert request('/api/data', {'key': 'pacientes', 'delta': rm})[0] == 409

    # Counters never conflict: the highest value wins.
    ids = request('/api/data')[1]['data']['nextIds']
    assert request('/api/data', {'key': 'nextIds', 'value': {**ids, 'pac': 50}, 'baseValue': {}})[0] == 200
    assert request('/api/data', {'key': 'nextIds', 'value': {**ids, 'pac': 40}, 'baseValue': ids})[0] == 200
    assert request('/api/data')[1]['data']['nextIds']['pac'] == 50

    # Invoices saved from the browser keep their server-side XML.
    inv = request('/api/data')[1]['data']['facturas']
    changed = json.loads(json.dumps(inv)); changed[0]['nota'] = 'ok'
    assert request('/api/data', {'key': 'facturas', 'value': changed, 'baseValue': inv})[0] == 200
    with app.db(read_only=True) as conn:
        saved = app.get_json_key(conn, 'facturas')[0]
        assert saved['nota'] == 'ok' and saved['xml'].startswith('<x/>') and saved['signedXml'] == '<s/>'

    # New upload: content goes to clinical_files, opened on demand.
    files = request('/api/data')[1]['data']['archivosClinicos']
    upload = json.loads(json.dumps(files)); upload['1'].insert(0, {'id': 12, 'nombre': 'lab.png', 'mime': 'image/png', 'dataUrl': PNG})
    assert request('/api/data', {'key': 'archivosClinicos', 'value': upload, 'baseValue': files})[0] == 200
    files_after = request('/api/data')[1]['data']['archivosClinicos']
    assert [f['id'] for f in files_after['1']] == [12, 11] and all(f.get('hasFile') for f in files_after['1'])
    # A later save from the same browser (its base still has the dataUrl) is not a conflict.
    edited = json.loads(json.dumps(upload)); edited['1'][0]['descripcion'] = 'resultado'
    assert request('/api/data', {'key': 'archivosClinicos', 'value': edited, 'baseValue': upload})[0] == 200
    with app.db(read_only=True) as conn:
        assert 'dataUrl' not in conn.execute("select value from app_data where key='archivosClinicos'").fetchone()['value']
    code, body = request('/api/clinical/file', {'patientId': '1', 'fileId': 11})
    assert code == 200 and body['dataUrl'] == PNG, code
    assert request('/api/clinical/file', {'patientId': '1', 'fileId': 999})[0] == 404

    # Large JSON is gzip-compressed when the client accepts it.
    with app.db() as conn:
        app.set_json_key(conn, 'servicios', [{'id': i, 'nombre': 'Servicio %d' % i, 'precio': 10} for i in range(300)])
    status, headers, raw = request('/api/data', headers={'Accept-Encoding': 'gzip'}, raw=True)
    assert headers.get('Content-Encoding') == 'gzip' and json.loads(gzip.decompress(raw))['data']
    # Partial reload of selected collections.
    partial = request('/api/data?keys=pacientes,nextIds')[1]['data']
    assert set(partial) <= {'pacientes', 'nextIds', 'sriCertificateStatus'} and partial['pacientes']
    # Deep health check reaches the database.
    assert request('/api/health?deep=1')[1]['ok'] is True

    # Brute-force protection on login.
    state['token'] = ''
    codes = [request('/api/login', {'email': app.ADMIN_EMAIL, 'password': 'wrong'})[0] for _ in range(app.LOGIN_MAX_FAILURES + 1)]
    assert codes[-1] == 429, codes
    assert request('/api/login', {'email': app.ADMIN_EMAIL, 'password': app.ADMIN_PASSWORD})[0] == 429

    server.shutdown(); server.server_close(); temporary.cleanup()
    print('PASS record-level merge, compact deltas, counters, invoice XML preservation, clinical files table + migration, gzip, partial reload, deep health, login throttling, schema gate')


if __name__ == '__main__':
    main()
