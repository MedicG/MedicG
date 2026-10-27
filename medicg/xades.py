"""XAdES-BES (ETSI 1.3.2) enveloped signature in the format required by the SRI (Ecuador).

Ficha técnica de comprobantes electrónicos: XAdES-BES v1.3.2, UTF-8, enveloped, RSA-SHA1.
The signature references the comprobante (#comprobante), the KeyInfo certificate and the
SignedProperties, and carries SigningCertificate with IssuerSerial (not SigningCertificateV2).
"""
import base64
import datetime as dt
import hashlib
import random

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import Encoding
from lxml import etree

DS = "http://www.w3.org/2000/09/xmldsig#"
ETSI = "http://uri.etsi.org/01903/v1.3.2#"
C14N = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
NSMAP = {"ds": DS, "etsi": ETSI}


def _b64(data):
    return base64.b64encode(data).decode("ascii")


def _sha1(data):
    return _b64(hashlib.sha1(data).digest())


def _c14n(node):
    return etree.tostring(node, method="c14n", exclusive=False, with_comments=False)


def _el(parent, ns, tag, text=None, **attrs):
    node = etree.SubElement(parent, "{%s}%s" % (ns, tag), nsmap=NSMAP)
    for key, value in attrs.items():
        node.set(key, value)
    if text is not None:
        node.text = text
    return node


def _int_b64(value):
    length = (value.bit_length() + 7) // 8
    return _b64(value.to_bytes(length, "big"))


def sign(xml_text, private_key, certificate, signing_time=None):
    """Return the signed XML (str). ``xml_text`` must have a root with id="comprobante"."""
    parser = etree.XMLParser(remove_blank_text=False)
    root = etree.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text, parser)
    if root.get("id") != "comprobante":
        raise ValueError("El comprobante debe tener id=\"comprobante\".")
    n = str(random.randint(100000, 999999))
    ids = {
        "signature": "Signature" + n,
        "signed_info": "Signature-SignedInfo" + n,
        "signed_props": "Signature" + n + "-SignedProperties" + n,
        "signed_props_ref": "SignedPropertiesID" + n,
        "certificate": "Certificate" + n,
        "reference": "Reference-ID-" + n,
        "signature_value": "SignatureValue" + n,
        "object": "Signature" + n + "-Object" + n,
    }

    # 1) digest of the comprobante (enveloped transform: computed before the signature is added)
    doc_digest = _sha1(_c14n(root))

    cert_der = certificate.public_bytes(Encoding.DER)
    public = certificate.public_key().public_numbers()
    signing_time = signing_time or dt.datetime.now(dt.timezone(dt.timedelta(hours=-5)))

    signature = _el(root, DS, "Signature", Id=ids["signature"])
    signed_info = _el(signature, DS, "SignedInfo", Id=ids["signed_info"])
    _el(signed_info, DS, "CanonicalizationMethod", Algorithm=C14N)
    _el(signed_info, DS, "SignatureMethod", Algorithm=DS + "rsa-sha1")

    ref_props = _el(signed_info, DS, "Reference", Id=ids["signed_props_ref"], Type="http://uri.etsi.org/01903#SignedProperties", URI="#" + ids["signed_props"])
    _el(ref_props, DS, "DigestMethod", Algorithm=DS + "sha1")
    props_digest_node = _el(ref_props, DS, "DigestValue")

    ref_cert = _el(signed_info, DS, "Reference", URI="#" + ids["certificate"])
    _el(ref_cert, DS, "DigestMethod", Algorithm=DS + "sha1")
    cert_digest_node = _el(ref_cert, DS, "DigestValue")

    ref_doc = _el(signed_info, DS, "Reference", Id=ids["reference"], URI="#comprobante")
    transforms = _el(ref_doc, DS, "Transforms")
    _el(transforms, DS, "Transform", Algorithm=DS + "enveloped-signature")
    _el(ref_doc, DS, "DigestMethod", Algorithm=DS + "sha1")
    _el(ref_doc, DS, "DigestValue", doc_digest)

    signature_value = _el(signature, DS, "SignatureValue", Id=ids["signature_value"])

    key_info = _el(signature, DS, "KeyInfo", Id=ids["certificate"])
    x509_data = _el(key_info, DS, "X509Data")
    _el(x509_data, DS, "X509Certificate", _b64(cert_der))
    key_value = _el(key_info, DS, "KeyValue")
    rsa_value = _el(key_value, DS, "RSAKeyValue")
    _el(rsa_value, DS, "Modulus", _int_b64(public.n))
    _el(rsa_value, DS, "Exponent", _int_b64(public.e))

    obj = _el(signature, DS, "Object", Id=ids["object"])
    qualifying = _el(obj, ETSI, "QualifyingProperties", Target="#" + ids["signature"])
    signed_props = _el(qualifying, ETSI, "SignedProperties", Id=ids["signed_props"])
    sig_props = _el(signed_props, ETSI, "SignedSignatureProperties")
    _el(sig_props, ETSI, "SigningTime", signing_time.isoformat(timespec="seconds"))
    signing_cert = _el(sig_props, ETSI, "SigningCertificate")
    cert_node = _el(signing_cert, ETSI, "Cert")
    cert_digest = _el(cert_node, ETSI, "CertDigest")
    _el(cert_digest, DS, "DigestMethod", Algorithm=DS + "sha1")
    _el(cert_digest, DS, "DigestValue", _sha1(cert_der))
    issuer_serial = _el(cert_node, ETSI, "IssuerSerial")
    _el(issuer_serial, DS, "X509IssuerName", certificate.issuer.rfc4514_string())
    _el(issuer_serial, DS, "X509SerialNumber", str(certificate.serial_number))
    data_props = _el(signed_props, ETSI, "SignedDataObjectProperties")
    data_format = _el(data_props, ETSI, "DataObjectFormat", ObjectReference="#" + ids["reference"])
    _el(data_format, ETSI, "Description", "contenido comprobante")
    _el(data_format, ETSI, "MimeType", "text/xml")

    # 2) digests of KeyInfo and SignedProperties, canonicalized in place (document context)
    cert_digest_node.text = _sha1(_c14n(key_info))
    props_digest_node.text = _sha1(_c14n(signed_props))

    # 3) signature over the canonical SignedInfo
    value = private_key.sign(_c14n(signed_info), padding.PKCS1v15(), hashes.SHA1())
    signature_value.text = _b64(value)
    return etree.tostring(root, encoding="UTF-8", xml_declaration=True).decode("utf-8")
