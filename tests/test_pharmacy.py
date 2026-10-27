"""Pharmacy: products, lots, FEFO dispensing, e-prescriptions, cash account, kardex,
controlled substances, idempotency and SRI XML with mixed VAT. Temporary SQLite only."""
import datetime
import json
import sys
import tempfile
import threading
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import medicg_app as app
from medicg.entrypoint import ProductionHandler

PASSWORD = 'LocalTest-12345'


def main():
    temporary = tempfile.TemporaryDirectory()
    app.DB_DRIVER = 'sqlite'
    app.DB_PATH = Path(temporary.name) / 'pharmacy.sqlite3'
    app.ADMIN_EMAIL = 'admin@localhost.test'
    app.ADMIN_PASSWORD = PASSWORD
    app.init_db()
    with app.db() as conn:
        app.set_json_key(conn, 'pacientes', [{'id': 1, 'nombres': 'Ana', 'apellidos': 'Paz', 'cedula': '1710034065', 'esp': 'Medicina General'}])
        app.set_json_key(conn, 'medicos', [{'id': 1, 'nombre': 'Dra. Gómez', 'esp': 'Medicina General', 'cedula': '1700', 'sen': 'REG-1'}])
        users = app.get_json_key(conn, 'users')
        for uid, email, rol, extra, perms in ((2, 'farm@localhost.test', 'recepcion', {}, ['caja', 'farmacia']), (3, 'doc@localhost.test', 'medico', {'medicoId': 1}, None),
                                              (4, 'recep@localhost.test', 'recepcion', {}, None)):
            users.append({'id': uid, 'name': rol, 'last': 'Test', 'email': email, 'rol': rol, 'estado': 'activo', 'emailVerified': True,
                          'passHash': app.hash_password(PASSWORD), 'permissions': app.clean_permissions(perms, rol), **extra})
        app.set_json_key(conn, 'users', users)
        ids = app.get_json_key(conn, 'nextIds'); ids['user'] = 5; app.set_json_key(conn, 'nextIds', ids)

    class Quiet(ProductionHandler):
        def log_message(self, *args):
            pass
    server = app.ThreadingHTTPServer(('127.0.0.1', 0), Quiet)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = 'http://127.0.0.1:' + str(server.server_port)

    def call(token, path, payload=None):
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token} if token else {'Content-Type': 'application/json'}
        req = urllib.request.Request(base + path, data=None if payload is None else json.dumps(payload).encode(), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def login(email):
        return call('', '/api/login', {'email': email, 'password': PASSWORD})[1]['token']
    admin, farm, doc, recep = (login(e) for e in ('admin@localhost.test', 'farm@localhost.test', 'doc@localhost.test', 'recep@localhost.test'))
    ph = lambda token, payload: call(token, '/api/pharmacy', payload)
    day = lambda n: (datetime.date.today() + datetime.timedelta(days=n)).isoformat()

    # ---- products and lots
    assert ph(recep, {'action': 'product_save', 'nombre': 'X'})[0] == 409  # no pharmacy permission
    code, body = ph(farm, {'action': 'product_save', 'nombre': 'Paracetamol', 'concentracion': '500 mg', 'forma': 'Tableta', 'precioVenta': 0.10, 'stockMinimo': 10, 'registroSanitario': 'ARCSA-123'})
    assert code == 200 and body['product']['ivaTarifa'] == 0 and body['product']['codigo'] == 'FAR00001', body
    para = body['product']['id']
    gauze = ph(farm, {'action': 'product_save', 'nombre': 'Gasa estéril', 'forma': 'Insumo', 'categoria': 'Insumo médico', 'precioVenta': 1.00})[1]['product']
    assert gauze['ivaTarifa'] == 15
    clon = ph(farm, {'action': 'product_save', 'nombre': 'Clonazepam', 'concentracion': '2 mg', 'forma': 'Tableta', 'precioVenta': 0.5, 'controlado': True})[1]['product']['id']
    assert ph(farm, {'action': 'lot_receive', 'productId': para, 'lote': 'OLD', 'caducidad': day(-1), 'cantidad': 5})[0] == 409  # expired lot rejected
    assert ph(farm, {'action': 'lot_receive', 'productId': para, 'lote': 'L-LATE', 'caducidad': day(400), 'cantidad': 50, 'costoUnitario': 0.03})[0] == 200
    assert ph(farm, {'action': 'lot_receive', 'productId': para, 'lote': 'L-SOON', 'caducidad': day(30), 'cantidad': 8})[0] == 200
    assert ph(farm, {'action': 'lot_receive', 'productId': gauze['id'], 'lote': 'G1', 'caducidad': day(700), 'cantidad': 10})[0] == 200
    assert ph(farm, {'action': 'lot_receive', 'productId': clon, 'lote': 'C1', 'caducidad': day(300), 'cantidad': 30})[0] == 200
    assert ph(farm, {'action': 'lot_receive', 'productId': para, 'lote': 'L-SOON', 'caducidad': day(31), 'cantidad': 1})[0] == 409  # same lot, other expiry

    # ---- over-the-counter sale, FEFO, mixed VAT, pending account (no open box)
    assert ph(farm, {'action': 'dispense', 'requestId': 'otc-000000000001', 'patientId': 1, 'lines': [{'productId': clon, 'cantidad': 1}]})[0] == 409  # controlled
    assert ph(farm, {'action': 'dispense', 'requestId': 'otc-000000000002', 'patientId': 1, 'lines': [{'productId': para, 'cantidad': 1}], 'payments': [{'method': 'Efectivo', 'amount': 0.1}]})[0] == 409  # payment needs open box
    code, body = ph(farm, {'action': 'dispense', 'requestId': 'otc-000000000003', 'patientId': 1, 'lines': [{'productId': para, 'cantidad': 10}, {'productId': gauze['id'], 'cantidad': 2}]})
    assert code == 200, body
    inv = body['invoice']
    assert body['lines'][0]['lotes'] == [{'lotId': body['lines'][0]['lotes'][0]['lotId'], 'lote': 'L-SOON', 'caducidad': day(30), 'cantidad': 8},
                                         {'lotId': body['lines'][0]['lotes'][1]['lotId'], 'lote': 'L-LATE', 'caducidad': day(400), 'cantidad': 2}], body['lines']
    assert inv['sub'] == 3.0 and inv['iva'] == 0.3 and inv['total'] == 3.3 and inv['saldo'] == 3.3 and inv['estadoPago'] == 'Pendiente', inv
    replay = ph(farm, {'action': 'dispense', 'requestId': 'otc-000000000003', 'patientId': 1, 'lines': [{'productId': para, 'cantidad': 10}, {'productId': gauze['id'], 'cantidad': 2}]})[1]
    assert replay['replayed'] and replay['invoice']['id'] == inv['id']
    assert ph(farm, {'action': 'dispense', 'requestId': 'otc-000000000004', 'patientId': 1, 'lines': [{'productId': para, 'cantidad': 1000}]})[0] == 409  # stock
    # SRI XML from the pharmacy account: 0% medicine + 15% supply
    sri = app.sri_config({'ruc': '1790012345001'})
    xml = app.build_invoice_xml({**inv, 'sri': sri, 'claveAcceso': '1' * 49, 'secuencial': '000000001'}, {'nombres': 'Ana', 'cedula': '1710034065'}, {})
    totals = [(t.find('codigoPorcentaje').text, t.find('baseImponible').text, t.find('valor').text) for t in ET.fromstring(xml).iter('totalImpuesto')]
    assert totals == [('0', '1.00', '0.00'), ('4', '2.00', '0.30')], totals
    # the account is collectable from Caja
    assert call(farm, '/api/cash/open', {})[0] == 200
    code, body = call(farm, '/api/cash/payment', {'requestId': 'pay-0000000000001', 'invoiceId': inv['id'], 'expectedBalance': 3.3, 'payments': [{'method': 'Efectivo', 'amount': 3.3}]})
    assert code == 200 and body['invoice']['saldo'] == 0, body

    # ---- e-prescription from the doctor, dispensed in parts
    assert ph(recep, {'action': 'rx_create', 'patientId': 1, 'diagnostico': 'x', 'items': [{'productoId': para, 'cantidad': 1, 'posologia': 'x'}]})[0] == 409
    code, body = ph(doc, {'action': 'rx_create', 'patientId': 1, 'diagnostico': 'Faringitis', 'cie10': 'j02.9', 'validezDias': 10,
                          'items': [{'productoId': para, 'cantidad': 12, 'posologia': '1 tableta cada 8 horas', 'duracion': '4 días'},
                                    {'productoId': clon, 'cantidad': 10, 'posologia': '1 tableta en la noche'},
                                    {'nombre': 'Ibuprofeno', 'concentracion': '400 mg', 'cantidad': 6, 'posologia': 'cada 8 horas'}]})
    assert code == 200 and body['receta']['numero'] == 'RX-000001' and body['receta']['cie10'] == 'J02.9' and body['receta']['items'][1]['controlado'], body
    rx = body['receta']
    assert ph(doc, {'action': 'rx_create', 'patientId': 1, 'diagnostico': 'x', 'items': [{'productoId': para, 'cantidad': 1}]})[0] == 409  # posology required
    assert call(doc, '/api/pharmacy/queue')[0] == 403
    q = call(farm, '/api/pharmacy/queue')[1]['queue']
    assert len(q) == 1 and q[0]['numero'] == 'RX-000001' and 'antec' not in json.dumps(q)
    assert ph(farm, {'action': 'dispense', 'requestId': 'rx-00000000000001', 'patientId': 1, 'rxId': rx['id'], 'lines': [{'productId': para, 'cantidad': 13, 'rxIndex': 0}]})[0] == 409  # more than prescribed
    code, body = ph(farm, {'action': 'dispense', 'requestId': 'rx-00000000000002', 'patientId': 1, 'rxId': rx['id'],
                           'lines': [{'productId': para, 'cantidad': 12, 'rxIndex': 0}, {'productId': clon, 'cantidad': 5, 'rxIndex': 1}],
                           'payments': [{'method': 'Tarjeta débito', 'amount': 1.0}]})
    assert code == 200 and body['receta']['dispensacion']['estado'] == 'Parcial' and body['invoice']['total'] == 3.7 and body['invoice']['saldo'] == 2.7, body
    code, body = ph(farm, {'action': 'dispense', 'requestId': 'rx-00000000000003', 'patientId': 1, 'rxId': rx['id'], 'cerrarReceta': True,
                           'lines': [{'productId': clon, 'cantidad': 5, 'rxIndex': 1}]})
    assert code == 200 and body['receta']['dispensacion']['estado'] == 'Dispensada'
    assert call(farm, '/api/pharmacy/queue')[1]['queue'] == []
    assert ph(farm, {'action': 'dispense', 'requestId': 'rx-00000000000004', 'patientId': 1, 'rxId': rx['id'], 'lines': [{'productId': clon, 'cantidad': 1, 'rxIndex': 1}]})[0] == 409

    # ---- adjustments, write-offs and kardex
    lots = call(admin, '/api/data')[1]['data']['farmaciaLotes']
    late = next(l for l in lots if l['lote'] == 'L-LATE')
    assert late['cantidad'] == 36, late
    assert ph(farm, {'action': 'lot_write_off', 'lotId': late['id'], 'cantidad': 40, 'motivo': 'Dañado / roto'})[0] == 409
    assert ph(farm, {'action': 'lot_write_off', 'lotId': late['id'], 'cantidad': 1, 'motivo': 'Dañado / roto'})[0] == 200
    assert ph(farm, {'action': 'lot_adjust', 'lotId': late['id'], 'cantidad': -5, 'motivo': 'Otro'})[0] == 409  # 'Otro' needs a note
    assert ph(farm, {'action': 'lot_adjust', 'lotId': late['id'], 'cantidad': 2, 'motivo': 'Conteo físico'})[0] == 200
    moves = call(farm, '/api/pharmacy/kardex?productId=' + str(para))[1]['moves']
    kinds = [m['kind'] for m in moves]
    assert kinds[0] == 'Ajuste: Conteo físico' and 'Baja: Dañado / roto' in kinds and 'Dispensación' in kinds and 'Venta sin receta' in kinds and kinds[-1] == 'Ingreso', kinds
    assert moves[0]['balance'] == 37 and any(m['ref'].startswith('RX-000001') for m in moves)
    assert call(recep, '/api/pharmacy/kardex')[0] == 403

    # ---- e-prescriptions can't be altered through the generic save
    recetas = call(admin, '/api/data')[1]['data']['recetas']
    tampered = json.loads(json.dumps(recetas)); tampered['1'][0]['items'][0]['cantidad'] = 99
    assert call(admin, '/api/data', {'key': 'recetas', 'value': tampered, 'baseValue': recetas})[0] == 409
    assert call(admin, '/api/data', {'key': 'farmaciaLotes', 'value': [], 'baseValue': lots})[0] == 403

    server.shutdown(); server.server_close(); temporary.cleanup()
    print('PASS pharmacy products and lots, FEFO, mixed VAT accounts and SRI XML, Caja collection, e-prescription partial dispensing, controlled substances, idempotency, write-offs, kardex and protections')


if __name__ == '__main__':
    main()
