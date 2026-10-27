"""Electronic invoicing end to end with a test certificate and a simulated SRI.
Checks access key, XML content, per-line VAT, XAdES signature, SRI states and e-mail to the client."""
import base64
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
import medicg.mailer as mailer
from medicg.entrypoint import ProductionHandler

PASSWORD = 'LocalTest-12345'
SENT_MAIL, SRI_CALLS = [], []


def make_p12():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'PRUEBA FIRMA MEDIC G')])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=30)).sign(key, hashes.SHA256()))
    data = pkcs12.serialize_key_and_certificates(b'firma', key, cert, None, serialization.BestAvailableEncryption(b'clave123'))
    return base64.b64encode(data).decode(), cert


def verify_sri_signature(signed, cert):
    """Independent check of the SRI XAdES-BES format: references, digests, RSA-SHA1 value and signing certificate."""
    import hashlib
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization import Encoding
    from lxml import etree
    ns = {'ds': 'http://www.w3.org/2000/09/xmldsig#', 'etsi': 'http://uri.etsi.org/01903/v1.3.2#'}
    doc = etree.fromstring(signed.encode())
    sig = doc.find('ds:Signature', ns)
    assert sig is not None and doc.index(sig) == len(doc) - 1, 'enveloped signature must be the last child'
    si = sig.find('ds:SignedInfo', ns)
    assert si.find('ds:SignatureMethod', ns).get('Algorithm') == 'http://www.w3.org/2000/09/xmldsig#rsa-sha1'
    by_id = {el.get('Id') or el.get('id'): el for el in doc.iter() if el.get('Id') or el.get('id')}
    refs = si.findall('ds:Reference', ns)
    assert len(refs) == 3
    for ref in refs:
        uri = ref.get('URI')[1:]
        assert ref.find('ds:DigestMethod', ns).get('Algorithm') == 'http://www.w3.org/2000/09/xmldsig#sha1'
        target = by_id[uri]
        if uri == 'comprobante':
            copy = etree.fromstring(etree.tostring(target))
            copy.remove(copy.find('ds:Signature', ns))
            data = etree.tostring(copy, method='c14n')
        else:
            data = etree.tostring(target, method='c14n')
        assert base64.b64encode(hashlib.sha1(data).digest()).decode() == ref.findtext('ds:DigestValue', namespaces=ns), uri
    value = base64.b64decode(sig.findtext('ds:SignatureValue', namespaces=ns))
    cert.public_key().verify(value, etree.tostring(si, method='c14n'), padding.PKCS1v15(), hashes.SHA1())
    sc = sig.find('.//etsi:SignedSignatureProperties/etsi:SigningCertificate/etsi:Cert', ns)
    assert sc is not None and sig.find('.//etsi:SigningCertificateV2', ns) is None
    assert sc.findtext('etsi:CertDigest/ds:DigestValue', namespaces=ns) == base64.b64encode(hashlib.sha1(cert.public_bytes(Encoding.DER)).digest()).decode()
    assert sc.findtext('etsi:IssuerSerial/ds:X509SerialNumber', namespaces=ns) == str(cert.serial_number)
    embedded = base64.b64decode(sig.findtext('ds:KeyInfo/ds:X509Data/ds:X509Certificate', namespaces=ns))
    assert embedded == cert.public_bytes(Encoding.DER)
    try:  # third-party verification when signxml is available
        from signxml import XMLVerifier, SignatureConfiguration, SignatureMethod, DigestAlgorithm
        cfg = SignatureConfiguration(signature_methods=frozenset(SignatureMethod), digest_algorithms=frozenset(DigestAlgorithm), expect_references=3)
        XMLVerifier().verify(signed.encode(), x509_cert=cert.public_bytes(Encoding.PEM).decode(), expect_config=cfg)
    except ImportError:
        pass


def fake_reception(signed_xml, ambiente):
    SRI_CALLS.append(('recepcion', ambiente, signed_xml))
    root = ET.fromstring(signed_xml.encode())
    if 'DEVOLVER' in signed_xml:
        return {'estado': 'DEVUELTA', 'mensajes': [{'identificador': '35', 'mensaje': 'ARCHIVO NO CUMPLE ESTRUCTURA XML'}]}
    return {'estado': 'RECIBIDA', 'mensajes': []}


def fake_authorization(clave, ambiente):
    SRI_CALLS.append(('autorizacion', ambiente, clave))
    signed = next(c[2] for c in reversed(SRI_CALLS) if c[0] == 'recepcion')
    return {'estado': 'AUTORIZADO', 'numeroAutorizacion': clave, 'fechaAutorizacion': '2026-10-27T10:30:00-05:00',
            'ambiente': 'PRUEBAS' if ambiente == '1' else 'PRODUCCION', 'comprobante': signed, 'mensajes': []}


def main():
    temporary = tempfile.TemporaryDirectory()
    app.DB_DRIVER = 'sqlite'
    app.DB_PATH = Path(temporary.name) / 'sri.sqlite3'
    app.ADMIN_EMAIL = 'admin@localhost.test'
    app.ADMIN_PASSWORD = PASSWORD
    app.SRI_AUTH_SLEEP_SECONDS = 0
    app.sri_recepcion = fake_reception
    app.sri_autorizacion = fake_authorization
    mailer.send = lambda to, subject, text, html, attachments=None, config=None, conn=None: (SENT_MAIL.append((to, subject, attachments)) or True, '')
    app.init_db()
    p12, cert = make_p12()
    with app.db() as conn:
        app.set_json_key(conn, 'config', {'nombre': 'Centro de Especialidades Medic G', 'sriRuc': '0929826519001', 'sriRazonSocial': 'HERRERA RENDON GABRIELA',
                                          'sriDirMatriz': 'Cdla Martha de Roldos Mz 215 V7', 'sriEstab': '001', 'sriPtoEmi': '002', 'sriAmbiente': '1'})
        app.set_json_key(conn, 'pacientes', [
            {'id': 1, 'nombres': 'Clarissa', 'apellidos': 'García', 'cedula': '0953534484', 'email': 'clarissa@example.test', 'dir': 'Guayaquil'},
            {'id': 2, 'nombres': 'Sin', 'apellidos': 'Cedula', 'cedula': '', 'email': ''},
            {'id': 3, 'nombres': 'Mala', 'apellidos': 'Cedula', 'cedula': '0953534485', 'email': 'x@example.test'}])
        app.set_json_key(conn, 'sriCertificate', {'p12Base64': p12, 'password': 'clave123', 'filename': 'prueba.p12'})

    class Quiet(ProductionHandler):
        def log_message(self, *args):
            pass
    server = app.ThreadingHTTPServer(('127.0.0.1', 0), Quiet)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = 'http://127.0.0.1:' + str(server.server_port)

    def call(token, path, payload=None):
        headers = {'Content-Type': 'application/json', **({'Authorization': 'Bearer ' + token} if token else {})}
        req = urllib.request.Request(base + path, data=None if payload is None else json.dumps(payload).encode(), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    admin = call('', '/api/login', {'email': 'admin@localhost.test', 'password': PASSWORD})[1]['token']

    # Manual invoice: consultation 0% + a taxed item 15%
    code, body = call(admin, '/api/invoices', {'pac': 1, 'esp': 'Ginecología', 'pago': 'Tarjeta débito',
                                              'items': [{'desc': 'Consulta ginecológica', 'cant': 1, 'unit': 40, 'ivaRate': 0},
                                                        {'desc': 'Kit de curación', 'cant': 2, 'unit': 5, 'ivaRate': 15}]})
    assert code == 201, body
    inv = body['invoice']
    assert inv['id'].startswith('001-002-') and inv['iva'] == 1.5 and inv['total'] == 51.5, inv
    code, body = call(admin, '/api/invoices/sri-retry', {'id': inv['id']})
    assert code == 200, body
    inv = body['invoice']
    assert inv['sriEstado'] == 'AUTORIZADO' and body['emailSent'] is True, body
    clave = inv['claveAcceso']
    assert len(clave) == 49 and clave[8:10] == '01' and clave[10:23] == '0929826519001' and clave[23] == '1' and clave[24:30] == '001002', clave
    signed = next(c[2] for c in SRI_CALLS if c[0] == 'recepcion')
    root = ET.fromstring(signed.encode())
    assert root.findtext('infoTributaria/claveAcceso') == clave and root.findtext('infoTributaria/ptoEmi') == '002'
    assert root.findtext('infoFactura/tipoIdentificacionComprador') == '05'
    pagos = root.findall('infoFactura/pagos/pago')
    assert [p.findtext('formaPago') for p in pagos] == ['16'], 'débito with accent must map to 16'
    taxes = {t.findtext('codigoPorcentaje'): (t.findtext('baseImponible'), t.findtext('valor')) for t in root.findall('infoFactura/totalConImpuestos/totalImpuesto')}
    assert taxes == {'0': ('40.00', '0.00'), '4': ('10.00', '1.50')}, taxes
    assert root.findtext('infoFactura/importeTotal') == '51.50'
    verify_sri_signature(signed, cert)
    to, subject, attachments = SENT_MAIL[-1]
    assert to == 'clarissa@example.test' and {a['filename'] for a in attachments} == {f"RIDE-{inv['id']}.html", f"{inv['id']}.xml"}
    ride = next(a for a in attachments if a['filename'].startswith('RIDE'))['content'].decode()
    for text in ('AMBIENTE:</b> PRUEBAS', 'NÚMERO DE AUTORIZACIÓN', clave, 'SUBTOTAL 0%', 'IVA 15%', '<svg'):
        assert text in ride, text
    assert 'SIN AUTORIZACIÓN' not in ride
    # Second request does not resend
    code, body = call(admin, '/api/invoices/sri-retry', {'id': inv['id']})
    assert body.get('alreadyAuthorized') and len(SENT_MAIL) == 1

    # Cash-desk account (no access key yet) goes to the SRI with its own per-line VAT
    with app.db() as conn:
        from medicg.cash import create_account
        acc = create_account(conn, {'id': 1, 'rol': 'admin'}, app.get_json_key(conn, 'pacientes')[0],
                             [{'nombre': 'Ecografía', 'cantidad': 1, 'unit': 30, 'ivaRate': 0}], [], 'Cobro')
    assert acc['id'].startswith('001-002-') and int(acc['id'][-9:]) == int(inv['id'][-9:]) + 1 and 'claveAcceso' not in acc, acc
    code, body = call(admin, '/api/invoices/sri-retry', {'id': acc['id']})
    assert code == 200 and body['invoice']['sriEstado'] == 'AUTORIZADO', body
    assert body['invoice']['claveAcceso'][30:39] == acc['id'][-9:]

    # Validations: consumer final over $50 and invalid cédula are stopped before the SRI
    code, body = call(admin, '/api/invoices', {'pac': 2, 'esp': 'X', 'items': [{'desc': 'Cirugía', 'cant': 1, 'unit': 80, 'ivaRate': 0}]})
    calls = len(SRI_CALLS)
    code, body = call(admin, '/api/invoices/sri-retry', {'id': body['invoice']['id']})
    assert code == 400 and 'consumidor final' in body['error'] and len(SRI_CALLS) == calls, body
    code, body = call(admin, '/api/invoices', {'pac': 3, 'esp': 'X', 'items': [{'desc': 'Consulta', 'cant': 1, 'unit': 20, 'ivaRate': 0}]})
    code, body = call(admin, '/api/invoices/sri-retry', {'id': body['invoice']['id']})
    assert code == 400 and 'cédula' in body['error'], body

    # Switching to production rebuilds the key of invoices not yet received
    code, body = call(admin, '/api/invoices', {'pac': 1, 'esp': 'X', 'items': [{'desc': 'Consulta', 'cant': 1, 'unit': 20, 'ivaRate': 0}]})
    pending = body['invoice']
    assert pending['claveAcceso'][23] == '1'
    with app.db() as conn:
        cfg = app.get_json_key(conn, 'config'); cfg['sriAmbiente'] = '2'; app.set_json_key(conn, 'config', cfg)
    code, body = call(admin, '/api/invoices/sri-retry', {'id': pending['id']})
    assert code == 200 and body['invoice']['claveAcceso'][23] == '2' and SRI_CALLS[-1][1] == '2', body
    ride = SENT_MAIL[-1][2][0]['content'].decode()
    import re as _re; assert 'AMBIENTE:</b> PRODUCCIÓN' in ride, (len(SENT_MAIL), _re.findall('AMBIENTE:</b> [A-ZÓ]+', ride), SENT_MAIL[-1][1])

    # Returned by the SRI: message is kept, nothing is e-mailed and it can be retried
    code, body = call(admin, '/api/invoices', {'pac': 1, 'esp': 'X', 'items': [{'desc': 'DEVOLVER consulta', 'cant': 1, 'unit': 20, 'ivaRate': 0}]})
    mails = len(SENT_MAIL)
    code, body = call(admin, '/api/invoices/sri-retry', {'id': body['invoice']['id']})
    assert code == 200 and body['invoice']['sriEstado'] == 'DEVUELTA' and '35' in body['invoice']['sriMensaje'] and not body['emailSent'] and len(SENT_MAIL) == mails, body
    print('PASS SRI: access key, per-line VAT, payment codes, XAdES signature, authorization, RIDE and e-mail to client, cash-desk accounts, validations, pruebas→producción, returned documents')


if __name__ == '__main__':
    main()
