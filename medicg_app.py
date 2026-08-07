from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from email.message import EmailMessage
from email.utils import formataddr
import base64
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import smtplib
import sqlite3
import time
import urllib.error
import urllib.request
from decimal import Decimal, ROUND_HALF_UP
from html import escape as html_escape
import xml.etree.ElementTree as ET

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("MEDICG_DB_PATH", BASE_DIR / "medicg.sqlite3"))
DATABASE_URL = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("POSTGRES_URL")
    or os.environ.get("POSTGRES_URL_NON_POOLING")
    or os.environ.get("POSTGRES_PRISMA_URL")
    or os.environ.get("POSTGRES_DATABASE_URL")
    or os.environ.get("NEON_DATABASE_URL")
)
DB_DRIVER = "postgres" if DATABASE_URL else "sqlite"
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@medicg.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin123")
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
MAX_BODY_BYTES = int(os.environ.get("MAX_BODY_BYTES", str(12 * 1024 * 1024)))
PUBLIC_APP_URL = os.environ.get("PUBLIC_APP_URL", "").rstrip("/")
PUBLIC_API_URL = os.environ.get("PUBLIC_API_URL", "").rstrip("/")
VERCEL_URL = os.environ.get("VERCEL_URL", "").rstrip("/")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER or ADMIN_EMAIL)
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "Medic G")
SMTP_TLS = os.environ.get("SMTP_TLS", "true").lower() not in ("0", "false", "no")
SMTP_SSL = os.environ.get("SMTP_SSL", "false").lower() in ("1", "true", "yes")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM = os.environ.get("RESEND_FROM", SMTP_FROM)
RESEND_ENDPOINT = os.environ.get("RESEND_ENDPOINT", "https://api.resend.com/emails")
SRI_CERT_P12_BASE64 = os.environ.get("SRI_CERT_P12_BASE64", "")
SRI_CERT_P12_PATH = os.environ.get("SRI_CERT_P12_PATH", "")
SRI_CERT_PASSWORD = os.environ.get("SRI_CERT_PASSWORD", "")
SRI_AUTH_RETRIES = int(os.environ.get("SRI_AUTH_RETRIES", "4"))
SRI_AUTH_SLEEP_SECONDS = float(os.environ.get("SRI_AUTH_SLEEP_SECONDS", "1.2"))
SRI_TIMEOUT_SECONDS = int(os.environ.get("SRI_TIMEOUT_SECONDS", "18"))
SHOW_VERIFICATION_LINK = os.environ.get("SHOW_VERIFICATION_LINK", "false").lower() in ("1", "true", "yes")
SESSIONS = {}
ALLOWED_PERMISSIONS = {
    "dashboard", "agenda", "hce", "facturacion", "reportes", "pacientes",
    "medicos", "especialidades", "seguros", "quirofanos", "servicios",
    "examenes", "caja", "config",
}
ROLE_DEFAULT_PERMISSIONS = {
    "admin": sorted(ALLOWED_PERMISSIONS),
    "recepcion": ["dashboard", "agenda", "caja"],
    "secretaria": ["dashboard", "agenda", "caja"],
    "asistente": ["agenda", "caja"],
    "medico": ["dashboard", "agenda", "hce"],
    "paciente": [],
    "pendiente": [],
}
MOJIBAKE_REPLACEMENTS = {
    "GestiÃƒÂ³n": "GestiÃ³n",
    "MÃƒÂ©dica": "MÃ©dica",
    "MÃƒÂ©dicas": "MÃ©dicas",
    "MÃƒÂ©dico": "MÃ©dico",
    "mÃƒÂ©dico": "mÃ©dico",
    "mÃƒÂ©dicos": "mÃ©dicos",
    "ClÃƒÂ­nica": "ClÃ­nica",
    "ElectrÃƒÂ³nica": "ElectrÃ³nica",
    "FacturaciÃƒÂ³n": "FacturaciÃ³n",
    "estadÃƒÂ­sticas": "estadÃ­sticas",
    "sesiÃƒÂ³n": "sesiÃ³n",
    "SesiÃƒÂ³n": "SesiÃ³n",
    "electrÃƒÂ³nico": "electrÃ³nico",
    "ContraseÃƒÂ±a": "ContraseÃ±a",
    "contraseÃƒÂ±a": "contraseÃ±a",
    "RecepciÃƒÂ³n": "RecepciÃ³n",
    "ConfiguraciÃƒÂ³n": "ConfiguraciÃ³n",
    "dÃƒÂ­a": "dÃ­a",
    "PediatrÃƒÂ­a": "PediatrÃ­a",
    "CardiologÃƒÂ­a": "CardiologÃ­a",
    "DermatologÃƒÂ­a": "DermatologÃ­a",
    "NeurologÃƒÂ­a": "NeurologÃ­a",
    "PÃƒÂ©rez": "PÃ©rez",
    "PÃƒÂºblico": "PÃºblico",
    "MarÃƒÂ­a": "MarÃ­a",
    "MuÃƒÂ±oz": "MuÃ±oz",
    "IbÃƒÂ¡ÃƒÂ±ez": "IbÃ¡Ã±ez",
    "RÃƒÂ­os": "RÃ­os",
    "cirugÃƒÂ­as": "cirugÃ­as",
    "atenciÃƒÂ³n": "atenciÃ³n",
    "corazÃƒÂ³n": "corazÃ³n",
    "fÃƒÂ­sica": "fÃ­sica",
    "DiagnÃƒÂ³stico": "DiagnÃ³stico",
    "MÃƒÂ­n.": "MÃ­n.",
}


class DatabaseConnection:
    def __init__(self, connection, driver):
        self.connection = connection
        self.driver = driver

    def execute(self, sql, params=()):
        if self.driver == "postgres":
            sql = sql.replace("?", "%s")
        return self.connection.execute(sql, params or ())

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()
        return False


def db():
    if DB_DRIVER == "postgres":
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "Falta psycopg. Instala requirements.txt o configura Vercel para instalar dependencias."
            ) from exc
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=10)
        return DatabaseConnection(conn, "postgres")
    if os.environ.get("VERCEL") and os.environ.get("ALLOW_SQLITE_ON_VERCEL", "").lower() not in ("1", "true", "yes"):
        raise RuntimeError(
            "Base de datos no configurada en Vercel. Conecta Postgres/Neon y agrega DATABASE_URL, POSTGRES_URL o POSTGRES_URL_NON_POOLING."
        )
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return DatabaseConnection(conn, "sqlite")


def table_sqlite_audit():
    return (
        "create table if not exists audit_log("
        "id integer primary key autoincrement, ts text not null, user_id integer, "
        "email text, action text not null, data_key text, detail text)"
    )


def table_postgres_audit():
    return (
        "create table if not exists audit_log("
        "id bigserial primary key, ts text not null, user_id integer, "
        "email text, action text not null, data_key text, detail text)"
    )


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"{salt}${digest.hex()}"


def verify_password(password, stored):
    if not stored:
        return False
    if "$" not in stored:
        return password == stored
    salt, _digest = stored.split("$", 1)
    return secrets.compare_digest(hash_password(password, salt), stored)


def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def user_email_verified(user):
    return bool(user.get("emailVerified", user.get("estado", "activo") == "activo"))


def app_base_url(handler):
    if PUBLIC_API_URL:
        return PUBLIC_API_URL
    if VERCEL_URL:
        return VERCEL_URL if VERCEL_URL.startswith("http") else f"https://{VERCEL_URL}"
    if PUBLIC_APP_URL:
        return PUBLIC_APP_URL
    origin = handler.headers.get("Origin", "").rstrip("/")
    if origin and not origin.endswith("github.io"):
        return origin
    proto = handler.headers.get("X-Forwarded-Proto", "").split(",")[0].strip().lower()
    proto = "https" if proto == "https" else "http"
    host = handler.headers.get("Host", f"{HOST}:{PORT}")
    return f"{proto}://{host}".rstrip("/")


def email_sender_address(sender_email=None):
    sender = sender_email or SMTP_FROM
    return formataddr((SMTP_FROM_NAME, sender)) if SMTP_FROM_NAME else sender


def email_text(name, link):
    return (
        f"Hola {name},\n\n"
        "Gracias por registrarte en Medic G.\n\n"
        "Para activar tu cuenta y poder iniciar sesion, verifica tu correo en este enlace:\n"
        f"{link}\n\n"
        "Este enlace vence por seguridad. Si no solicitaste esta cuenta, puedes ignorar este mensaje."
    )


def email_html(name, link):
    safe_name = str(name or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_link = str(link or "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
    return f"""
    <div style="font-family:Arial,sans-serif;background:#f6f9fb;padding:24px;color:#1f2937;">
      <div style="max-width:560px;margin:auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;padding:26px;">
        <h1 style="margin:0 0 12px;color:#0f766e;font-size:24px;">Verifica tu cuenta Medic G</h1>
        <p>Hola {safe_name},</p>
        <p>Gracias por registrarte en Medic G. Para activar tu cuenta y poder iniciar sesion, confirma tu correo.</p>
        <p style="margin:24px 0;"><a href="{safe_link}" style="background:#0f766e;color:#fff;text-decoration:none;padding:12px 18px;border-radius:10px;font-weight:700;display:inline-block;">Verificar mi correo</a></p>
        <p style="font-size:13px;color:#6b7280;">Si el boton no funciona, copia este enlace en tu navegador:<br>{safe_link}</p>
        <p style="font-size:13px;color:#6b7280;">Si no solicitaste esta cuenta, puedes ignorar este mensaje.</p>
      </div>
    </div>
    """


def email_configured():
    return bool((RESEND_API_KEY and RESEND_FROM) or (SMTP_HOST and SMTP_FROM))


def send_with_resend(to_email, subject, text_body, html_body):
    sender = RESEND_FROM if "<" in RESEND_FROM else email_sender_address(RESEND_FROM)
    payload = json.dumps({
        "from": sender,
        "to": [to_email],
        "subject": subject,
        "text": text_body,
        "html": html_body,
    }).encode("utf-8")
    req = urllib.request.Request(
        RESEND_ENDPOINT,
        data=payload,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status < 200 or resp.status >= 300:
            return False, f"Resend respondio con estado {resp.status}"
    return True, ""


def send_with_smtp(to_email, subject, text_body, html_body):
    if not (SMTP_HOST and SMTP_FROM):
        return False, "SMTP no configurado"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_sender_address()
    msg["To"] = to_email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    if SMTP_SSL:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            if SMTP_USER and SMTP_PASSWORD:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            smtp.ehlo()
            if SMTP_TLS:
                smtp.starttls()
                smtp.ehlo()
            if SMTP_USER and SMTP_PASSWORD:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
    return True, ""


def send_verification_email(to_email, name, link):
    if not email_configured():
        return False, "Configura SMTP_HOST/SMTP_FROM o RESEND_API_KEY/RESEND_FROM"
    subject = "Verifica tu cuenta Medic G"
    text_body = email_text(name, link)
    html_body = email_html(name, link)
    try:
        if RESEND_API_KEY and RESEND_FROM:
            return send_with_resend(to_email, subject, text_body, html_body)
        return send_with_smtp(to_email, subject, text_body, html_body)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return False, f"Error Resend {exc.code}: {detail}"
    except Exception as exc:
        return False, str(exc)

class SRIIntegrationError(Exception):
    pass


SRI_RECEPTION_ENDPOINTS = {
    "1": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline",
    "2": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline",
}
SRI_AUTH_ENDPOINTS = {
    "1": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline",
    "2": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline",
}


def clean_digits(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def sri_bool(value, default=False):
    if value is None or value == "":
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "si", "on", "prod", "produccion")


def money_decimal(value):
    try:
        return Decimal(str(value or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.00")


def money_text(value):
    return f"{money_decimal(value):.2f}"


def parse_invoice_date(value):
    raw = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    return dt.date.today()


def sri_config(config):
    cfg = config or {}
    ambiente_raw = os.environ.get("SRI_AMBIENTE") or cfg.get("sriAmbiente") or "1"
    ambiente = "2" if str(ambiente_raw).strip().lower() in ("2", "prod", "produccion", "production") else "1"
    iva_rate = money_decimal(os.environ.get("SRI_IVA_RATE") or cfg.get("sriIvaRate") or "15")
    iva_code = os.environ.get("SRI_IVA_CODE") or cfg.get("sriIvaCode") or ("4" if iva_rate == Decimal("15.00") else "2" if iva_rate == Decimal("12.00") else "0")
    auto_env = os.environ.get("SRI_AUTO_SEND")
    auto_send = sri_bool(auto_env, bool(cfg.get("sriAutoSend", True))) if auto_env is not None else bool(cfg.get("sriAutoSend", True))
    return {
        "ambiente": ambiente,
        "tipoEmision": "1",
        "ruc": clean_digits(os.environ.get("SRI_RUC") or cfg.get("sriRuc") or cfg.get("ruc")),
        "razonSocial": os.environ.get("SRI_RAZON_SOCIAL") or cfg.get("sriRazonSocial") or cfg.get("nombre") or "Centro Medico",
        "nombreComercial": os.environ.get("SRI_NOMBRE_COMERCIAL") or cfg.get("sriNombreComercial") or cfg.get("nombre") or "Medic G",
        "dirMatriz": os.environ.get("SRI_DIR_MATRIZ") or cfg.get("sriDirMatriz") or cfg.get("dir") or "",
        "dirEstablecimiento": os.environ.get("SRI_DIR_ESTABLECIMIENTO") or cfg.get("sriDirEstablecimiento") or cfg.get("dir") or "",
        "estab": (os.environ.get("SRI_ESTAB") or cfg.get("sriEstab") or "001").zfill(3)[:3],
        "ptoEmi": (os.environ.get("SRI_PTO_EMI") or cfg.get("sriPtoEmi") or "001").zfill(3)[:3],
        "obligadoContabilidad": (os.environ.get("SRI_OBLIGADO_CONTABILIDAD") or cfg.get("sriObligadoContabilidad") or "NO").upper(),
        "contribuyenteEspecial": os.environ.get("SRI_CONTRIBUYENTE_ESPECIAL") or cfg.get("sriContribuyenteEspecial") or "",
        "ivaRate": iva_rate,
        "ivaCode": str(iva_code),
        "autoSend": auto_send,
    }


def sri_mod11(body):
    factors = [2, 3, 4, 5, 6, 7]
    total = 0
    for idx, digit in enumerate(reversed(body)):
        total += int(digit) * factors[idx % len(factors)]
    check = 11 - (total % 11)
    if check == 11:
        return "0"
    if check == 10:
        return "1"
    return str(check)


def build_access_key(fecha, sri, secuencial):
    ruc = clean_digits(sri.get("ruc"))
    if len(ruc) != 13:
        raise SRIIntegrationError("Configura un RUC valido de 13 digitos para facturacion electronica SRI")
    numeric_code = clean_digits(os.environ.get("SRI_NUMERIC_CODE") or f"{int(time.time()) % 100000000:08d}").zfill(8)[-8:]
    body = (
        fecha.strftime("%d%m%Y")
        + "01"
        + ruc
        + sri["ambiente"]
        + sri["estab"]
        + sri["ptoEmi"]
        + str(secuencial).zfill(9)[-9:]
        + numeric_code
        + sri["tipoEmision"]
    )
    return body + sri_mod11(body)


def id_type_for_patient(patient):
    doc = clean_digits(patient.get("cedula") or patient.get("ruc") or patient.get("documento"))
    if len(doc) == 13:
        return "04", doc
    if len(doc) == 10:
        return "05", doc
    if doc:
        return "06", doc
    return "07", "9999999999999"


def payment_code(payment):
    value = str(payment or "").lower()
    if "debito" in value or "debito" in value:
        return "16"
    if "credito" in value or "credito" in value or "tarjeta" in value:
        return "19"
    if "transfer" in value or "seguro" in value or "iess" in value:
        return "20"
    return "01"


def add_text(parent, name, text):
    child = ET.SubElement(parent, name)
    child.text = str(text if text is not None else "")
    return child


def build_invoice_xml(invoice, patient, config):
    sri = invoice["sri"]
    fecha = parse_invoice_date(invoice.get("fecha"))
    tipo_id, identificacion = id_type_for_patient(patient)
    subtotal = money_decimal(invoice.get("sub"))
    iva = money_decimal(invoice.get("iva"))
    total = money_decimal(invoice.get("total"))
    iva_rate = money_decimal(sri.get("ivaRate") or 15)
    root = ET.Element("factura", {"id": "comprobante", "version": "1.1.0"})
    info_trib = ET.SubElement(root, "infoTributaria")
    add_text(info_trib, "ambiente", sri["ambiente"])
    add_text(info_trib, "tipoEmision", sri["tipoEmision"])
    add_text(info_trib, "razonSocial", sri["razonSocial"][:300])
    add_text(info_trib, "nombreComercial", sri["nombreComercial"][:300])
    add_text(info_trib, "ruc", sri["ruc"])
    add_text(info_trib, "claveAcceso", invoice["claveAcceso"])
    add_text(info_trib, "codDoc", "01")
    add_text(info_trib, "estab", sri["estab"])
    add_text(info_trib, "ptoEmi", sri["ptoEmi"])
    add_text(info_trib, "secuencial", invoice["secuencial"])
    add_text(info_trib, "dirMatriz", sri["dirMatriz"][:300])

    info_fact = ET.SubElement(root, "infoFactura")
    add_text(info_fact, "fechaEmision", fecha.strftime("%d/%m/%Y"))
    add_text(info_fact, "dirEstablecimiento", sri["dirEstablecimiento"][:300])
    if sri.get("contribuyenteEspecial"):
        add_text(info_fact, "contribuyenteEspecial", sri["contribuyenteEspecial"])
    add_text(info_fact, "obligadoContabilidad", sri["obligadoContabilidad"] if sri["obligadoContabilidad"] in ("SI", "NO") else "NO")
    add_text(info_fact, "tipoIdentificacionComprador", tipo_id)
    buyer_name = f"{patient.get('nombres','')} {patient.get('apellidos','')}".strip() or "CONSUMIDOR FINAL"
    add_text(info_fact, "razonSocialComprador", buyer_name[:300])
    add_text(info_fact, "identificacionComprador", identificacion)
    add_text(info_fact, "direccionComprador", (patient.get("dir") or "Consumidor final")[:300])
    add_text(info_fact, "totalSinImpuestos", money_text(subtotal))
    add_text(info_fact, "totalDescuento", "0.00")
    total_imp = ET.SubElement(info_fact, "totalConImpuestos")
    imp = ET.SubElement(total_imp, "totalImpuesto")
    add_text(imp, "codigo", "2")
    add_text(imp, "codigoPorcentaje", sri["ivaCode"])
    add_text(imp, "baseImponible", money_text(subtotal))
    add_text(imp, "valor", money_text(iva))
    add_text(info_fact, "propina", "0.00")
    add_text(info_fact, "importeTotal", money_text(total))
    add_text(info_fact, "moneda", "DOLAR")
    pagos = ET.SubElement(info_fact, "pagos")
    pago = ET.SubElement(pagos, "pago")
    add_text(pago, "formaPago", payment_code(invoice.get("pago")))
    add_text(pago, "total", money_text(total))
    add_text(pago, "plazo", "0")
    add_text(pago, "unidadTiempo", "dias")

    detalles = ET.SubElement(root, "detalles")
    for idx, item in enumerate(invoice.get("items") or [], start=1):
        qty = money_decimal(item.get("cant") or 1)
        unit = money_decimal(item.get("unit"))
        line_base = money_decimal(item.get("total") or (qty * unit))
        line_tax = money_decimal(line_base * iva_rate / Decimal("100"))
        det = ET.SubElement(detalles, "detalle")
        add_text(det, "codigoPrincipal", str(item.get("codigo") or f"MED{idx:03d}"))
        add_text(det, "descripcion", str(item.get("desc") or "Servicio medico")[:300])
        add_text(det, "cantidad", money_text(qty))
        add_text(det, "precioUnitario", money_text(unit))
        add_text(det, "descuento", "0.00")
        add_text(det, "precioTotalSinImpuesto", money_text(line_base))
        impuestos = ET.SubElement(det, "impuestos")
        impuesto = ET.SubElement(impuestos, "impuesto")
        add_text(impuesto, "codigo", "2")
        add_text(impuesto, "codigoPorcentaje", sri["ivaCode"])
        add_text(impuesto, "tarifa", money_text(iva_rate))
        add_text(impuesto, "baseImponible", money_text(line_base))
        add_text(impuesto, "valor", money_text(line_tax))

    info_ad = ET.SubElement(root, "infoAdicional")
    if patient.get("email"):
        add_text(info_ad, "campoAdicional", patient.get("email")).set("nombre", "Email")
    add_text(info_ad, "campoAdicional", buyer_name[:300]).set("nombre", "Paciente")
    add_text(info_ad, "campoAdicional", f"HCE-{str(patient.get('id') or 0).zfill(4)}").set("nombre", "HistoriaClinica")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def normalize_cert_base64(value):
    raw = str(value or "").strip()
    if raw.lower().startswith("data:") and "," in raw:
        raw = raw.split(",", 1)[1]
    return "".join(raw.split())


def saved_sri_certificate_status(cert):
    cert = cert if isinstance(cert, dict) else {}
    has_env_cert = bool(normalize_cert_base64(SRI_CERT_P12_BASE64))
    saved_b64 = normalize_cert_base64(cert.get("p12Base64"))
    configured = bool(has_env_cert or saved_b64)
    return {
        "configured": configured,
        "source": "Variables privadas de Vercel" if has_env_cert else ("Base de datos" if saved_b64 else "No configurado"),
        "filename": "SRI_CERT_P12_BASE64" if has_env_cert else cert.get("filename", ""),
        "updatedAt": "" if has_env_cert else cert.get("updatedAt", ""),
        "hasPassword": bool(SRI_CERT_PASSWORD or cert.get("password")),
        "envLocked": has_env_cert,
    }


def get_sri_certificate(conn):
    env_b64 = normalize_cert_base64(SRI_CERT_P12_BASE64)
    if env_b64:
        return {
            "p12Base64": env_b64,
            "password": SRI_CERT_PASSWORD,
            "filename": "SRI_CERT_P12_BASE64",
            "source": "Variables privadas de Vercel",
        }
    saved = get_json_key(conn, "sriCertificate", {}) or {}
    return {
        "p12Base64": normalize_cert_base64(saved.get("p12Base64")),
        "password": saved.get("password") or SRI_CERT_PASSWORD,
        "filename": saved.get("filename", ""),
        "updatedAt": saved.get("updatedAt", ""),
        "uploadedBy": saved.get("uploadedBy", ""),
        "source": "Base de datos" if saved.get("p12Base64") else "No configurado",
    }


def sri_certificate_status(conn):
    saved = get_json_key(conn, "sriCertificate", {}) or {}
    return saved_sri_certificate_status(saved)


def load_sri_certificate_bytes(cert_info=None):
    cert_info = cert_info or {}
    cert_b64 = normalize_cert_base64(cert_info.get("p12Base64") or SRI_CERT_P12_BASE64)
    if cert_b64:
        try:
            return base64.b64decode(cert_b64, validate=True)
        except Exception as exc:
            raise SRIIntegrationError("El certificado .p12/.pfx guardado no es valido. Vuelve a subirlo desde Configuracion.") from exc
    if SRI_CERT_P12_PATH:
        cert_path = Path(SRI_CERT_P12_PATH)
        if cert_path.exists():
            return cert_path.read_bytes()
    raise SRIIntegrationError("Sube el certificado .p12/.pfx y su clave en Configuracion > Facturacion electronica SRI, o configura SRI_CERT_P12_BASE64 y SRI_CERT_PASSWORD en Vercel")


def sign_invoice_xml(unsigned_xml, cert_info=None):
    try:
        from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, pkcs12
        from signxml import methods
        from signxml.xades import XAdESDataObjectFormat, XAdESSigner
        from lxml import etree
    except Exception as exc:
        raise SRIIntegrationError("Faltan dependencias para firma XAdES. Reinstala requirements.txt en Vercel.") from exc
    try:
        cert_info = cert_info or {}
        cert_password = cert_info.get("password") or SRI_CERT_PASSWORD
        key, cert, _extra = pkcs12.load_key_and_certificates(
            load_sri_certificate_bytes(cert_info),
            cert_password.encode("utf-8") if cert_password else None,
        )
        if not key or not cert:
            raise SRIIntegrationError("El certificado P12 no contiene clave privada o certificado valido")
        key_pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
        cert_pem = cert.public_bytes(Encoding.PEM)
        root = etree.fromstring(unsigned_xml.encode("utf-8"))
        signer = XAdESSigner(
            method=methods.enveloped,
            signature_algorithm="rsa-sha256",
            digest_algorithm="sha256",
            c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
            data_object_format=XAdESDataObjectFormat(Description="Factura electronica SRI", MimeType="text/xml"),
        )
        signer.use_deprecated_legacy_signing_certificate = True
        signed = signer.sign(root, key=key_pem, cert=cert_pem, reference_uri="#comprobante")
        return etree.tostring(signed, encoding="utf-8", xml_declaration=True).decode("utf-8")
    except SRIIntegrationError:
        raise
    except Exception as exc:
        raise SRIIntegrationError(f"No se pudo firmar el XML con el certificado digital: {exc}") from exc


def xml_local_name(tag):
    return str(tag).split("}", 1)[-1]


def xml_first_text(root, name):
    for node in root.iter():
        if xml_local_name(node.tag) == name and node.text:
            return node.text.strip()
    return ""


def xml_messages(root):
    messages = []
    for msg in root.iter():
        if xml_local_name(msg.tag) != "mensaje":
            continue
        detail = {}
        for child in list(msg):
            detail[xml_local_name(child.tag)] = (child.text or "").strip()
        if detail:
            messages.append(detail)
    return messages


def sri_soap_request(url, action_body):
    envelope = f'''<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Header/>
  <soapenv:Body>{action_body}</soapenv:Body>
</soapenv:Envelope>'''.encode("utf-8")
    req = urllib.request.Request(
        url,
        data=envelope,
        method="POST",
        headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""},
    )
    try:
        with urllib.request.urlopen(req, timeout=SRI_TIMEOUT_SECONDS) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SRIIntegrationError(f"SRI respondio HTTP {exc.code}: {detail[:500]}") from exc
    except Exception as exc:
        raise SRIIntegrationError(f"No se pudo conectar con el SRI: {exc}") from exc


def sri_recepcion(signed_xml, ambiente):
    payload = base64.b64encode(signed_xml.encode("utf-8")).decode("ascii")
    body = f'''<validarComprobante xmlns="http://ec.gob.sri.ws.recepcion">
  <xml>{payload}</xml>
</validarComprobante>'''
    raw = sri_soap_request(SRI_RECEPTION_ENDPOINTS[ambiente], body)
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise SRIIntegrationError(f"Respuesta SRI recepcion invalida: {raw[:300]}") from exc
    return {"estado": xml_first_text(root, "estado") or "SIN_RESPUESTA", "mensajes": xml_messages(root), "raw": raw[:3000]}


def sri_autorizacion(clave, ambiente):
    body = f'''<autorizacionComprobante xmlns="http://ec.gob.sri.ws.autorizacion">
  <claveAccesoComprobante>{html_escape(clave)}</claveAccesoComprobante>
</autorizacionComprobante>'''
    raw = sri_soap_request(SRI_AUTH_ENDPOINTS[ambiente], body)
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise SRIIntegrationError(f"Respuesta SRI autorizacion invalida: {raw[:300]}") from exc
    auth_node = None
    for node in root.iter():
        if xml_local_name(node.tag) == "autorizacion":
            auth_node = node
            break
    if auth_node is None:
        return {"estado": xml_first_text(root, "estado") or "EN_PROCESO", "mensajes": xml_messages(root), "raw": raw[:3000]}
    comprobante = xml_first_text(auth_node, "comprobante")
    return {
        "estado": xml_first_text(auth_node, "estado") or "EN_PROCESO",
        "numeroAutorizacion": xml_first_text(auth_node, "numeroAutorizacion"),
        "fechaAutorizacion": xml_first_text(auth_node, "fechaAutorizacion"),
        "ambiente": xml_first_text(auth_node, "ambiente"),
        "comprobante": comprobante,
        "mensajes": xml_messages(auth_node),
        "raw": raw[:3000],
    }


def ride_html(invoice, patient, config, ticket=False):
    cfg = config or {}
    rows = "".join(
        f"<tr><td>{html_escape(str(i.get('desc','')))}</td><td>{html_escape(str(i.get('cant',1)))}</td><td>{money_text(i.get('unit'))}</td><td>{money_text(i.get('total'))}</td></tr>"
        for i in (invoice.get("items") or [])
    )
    patient_name = f"{patient.get('nombres','')} {patient.get('apellidos','')}".strip()
    width = "width:80mm;font-size:11px;" if ticket else "max-width:760px;"
    return f"""<!doctype html><html lang='es'><meta charset='utf-8'><title>RIDE {html_escape(invoice.get('id',''))}</title>
<body style='font-family:Arial,sans-serif;color:#111;margin:0;padding:18px;{width}'>
  <div style='display:flex;gap:12px;align-items:center;border-bottom:2px solid #0f766e;padding-bottom:10px;margin-bottom:12px;'>
    <img src='{html_escape(cfg.get('logo') or 'assets/medicg-logo.jpg')}' style='width:72px;height:72px;object-fit:contain;'>
    <div><h2 style='margin:0;'>{html_escape(cfg.get('nombre') or 'Centro Medico')}</h2><div>RUC: {html_escape((invoice.get('sri') or {}).get('ruc') or cfg.get('ruc') or '')}</div><div>{html_escape(cfg.get('dir') or '')}</div></div>
  </div>
  <h3>RIDE - Factura electronica</h3>
  <p><b>No.:</b> {html_escape(invoice.get('id',''))}<br><b>Fecha:</b> {html_escape(invoice.get('fecha',''))}<br><b>Estado SRI:</b> {html_escape(invoice.get('sriEstado') or invoice.get('estado',''))}</p>
  <p><b>Cliente:</b> {html_escape(patient_name)}<br><b>Identificacion:</b> {html_escape(patient.get('cedula') or '9999999999999')}<br><b>Email:</b> {html_escape(patient.get('email') or '')}</p>
  <table width='100%' border='1' cellspacing='0' cellpadding='6'><thead><tr><th>Detalle</th><th>Cant.</th><th>P.Unit.</th><th>Total</th></tr></thead><tbody>{rows}</tbody></table>
  <div style='text-align:right;margin-top:12px;'><div>Subtotal: ${money_text(invoice.get('sub'))}</div><div>IVA: ${money_text(invoice.get('iva'))}</div><h3>Total: ${money_text(invoice.get('total'))}</h3></div>
  <p style='word-break:break-all;'><b>Clave de acceso:</b><br>{html_escape(invoice.get('claveAcceso') or '')}</p>
  <p style='word-break:break-all;'><b>Autorizacion:</b><br>{html_escape(invoice.get('autorizacion') or '')}</p>
</body></html>"""


def send_transaction_email(to_email, subject, text_body, html_body, attachments=None):
    attachments = attachments or []
    if not email_configured():
        return False, "Configura SMTP o Resend para enviar correos"
    try:
        if RESEND_API_KEY and RESEND_FROM:
            sender = RESEND_FROM if "<" in RESEND_FROM else email_sender_address(RESEND_FROM)
            payload = {
                "from": sender,
                "to": [to_email],
                "subject": subject,
                "text": text_body,
                "html": html_body,
            }
            if attachments:
                payload["attachments"] = [
                    {"filename": a["filename"], "content": base64.b64encode(a["content"]).decode("ascii")}
                    for a in attachments
                ]
            req = urllib.request.Request(
                RESEND_ENDPOINT,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status < 200 or resp.status >= 300:
                    return False, f"Resend respondio con estado {resp.status}"
            return True, ""
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = email_sender_address()
        msg["To"] = to_email
        msg.set_content(text_body)
        msg.add_alternative(html_body, subtype="html")
        for att in attachments:
            maintype, subtype = (att.get("mime") or "application/octet-stream").split("/", 1)
            msg.add_attachment(att["content"], maintype=maintype, subtype=subtype, filename=att["filename"])
        if SMTP_SSL:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
                if SMTP_USER and SMTP_PASSWORD:
                    smtp.login(SMTP_USER, SMTP_PASSWORD)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
                smtp.ehlo()
                if SMTP_TLS:
                    smtp.starttls(); smtp.ehlo()
                if SMTP_USER and SMTP_PASSWORD:
                    smtp.login(SMTP_USER, SMTP_PASSWORD)
                smtp.send_message(msg)
        return True, ""
    except urllib.error.HTTPError as exc:
        return False, exc.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return False, str(exc)


def send_invoice_email(invoice, patient, config):
    to_email = (patient.get("email") or "").strip()
    if not to_email:
        return False, "El paciente no tiene correo registrado"
    subject = f"Factura electronica {invoice.get('id')} - {config.get('nombre','Medic G')}"
    text = (
        f"Adjuntamos tu factura electronica {invoice.get('id')}\n"
        f"Estado SRI: {invoice.get('sriEstado') or invoice.get('estado')}\n"
        f"Total: ${money_text(invoice.get('total'))}\n"
        f"Clave de acceso: {invoice.get('claveAcceso') or ''}\n"
    )
    html = ride_html(invoice, patient, config)
    xml_content = (invoice.get("authorizedXml") or invoice.get("signedXml") or invoice.get("xml") or "").encode("utf-8")
    attachments = [
        {"filename": f"RIDE-{invoice.get('id')}.html", "content": html.encode("utf-8"), "mime": "text/html"},
    ]
    if xml_content:
        attachments.append({"filename": f"{invoice.get('id')}.xml", "content": xml_content, "mime": "application/xml"})
    return send_transaction_email(to_email, subject, text, html, attachments)


def can_invoice_sri(user):
    if not user:
        return False
    if user.get("rol") == "admin":
        return True
    perms = set(clean_permissions(user.get("permissions"), user.get("rol", "recepcion")))
    return bool({"facturacion", "caja"} & perms)


def prepare_invoice_from_payload(conn, user, payload):
    patients = get_json_key(conn, "pacientes", []) or []
    patient_id = int(payload.get("pac") or payload.get("patientId") or 0)
    patient = find_patient(patients, patient_id=patient_id)
    if not patient:
        raise SRIIntegrationError("Selecciona un paciente registrado para emitir factura")
    items = []
    for raw in payload.get("items") or []:
        desc = str(raw.get("desc") or raw.get("descripcion") or "").strip()
        qty = money_decimal(raw.get("cant") or raw.get("cantidad") or 1)
        unit = money_decimal(raw.get("unit") or raw.get("precio") or 0)
        if desc and qty > 0 and unit >= 0:
            items.append({"desc": desc, "cant": float(qty), "unit": float(unit), "total": float(money_decimal(qty * unit))})
    if not items:
        raise SRIIntegrationError("Agrega al menos un servicio o examen facturable")
    config = get_json_key(conn, "config", {}) or {}
    sri = sri_config(config)
    next_ids = get_json_key(conn, "nextIds", {}) or {}
    seq_int = next_id(next_ids, "fac", 1)
    secuencial = str(seq_int).zfill(9)[-9:]
    fecha = parse_invoice_date(payload.get("fecha"))
    subtotal = sum(money_decimal(i["total"]) for i in items)
    iva_rate = money_decimal(sri.get("ivaRate") or 15)
    iva = money_decimal(subtotal * iva_rate / Decimal("100"))
    total = money_decimal(subtotal + iva)
    clave = build_access_key(fecha, sri, secuencial)
    invoice = {
        "id": f"{sri['estab']}-{sri['ptoEmi']}-{secuencial}",
        "secuencial": secuencial,
        "claveAcceso": clave,
        "autorizacion": "",
        "fecha": fecha.isoformat(),
        "pac": patient_id,
        "esp": payload.get("esp") or patient.get("esp") or "General",
        "serv": ", ".join(i["desc"] for i in items),
        "items": items,
        "sub": float(subtotal),
        "iva": float(iva),
        "total": float(total),
        "pago": payload.get("pago") or "Efectivo",
        "estado": "Pendiente SRI",
        "sriEstado": "GENERADO",
        "sriMensaje": "XML generado pendiente de envio",
        "sri": {**sri, "ivaRate": float(iva_rate)},
        "emailAuto": bool(payload.get("emailAuto", True)),
        "emailEnviado": False,
        "createdAt": now_iso(),
        "createdBy": user.get("email") if user else "sistema",
    }
    invoice["xml"] = build_invoice_xml(invoice, patient, config)
    set_json_key(conn, "nextIds", next_ids)
    return invoice, patient, config


def send_invoice_to_sri(invoice, cert_info=None):
    invoice["signedXml"] = sign_invoice_xml(invoice["xml"], cert_info)
    reception = sri_recepcion(invoice["signedXml"], invoice["sri"]["ambiente"])
    invoice["sriRecepcion"] = reception
    if reception.get("estado") != "RECIBIDA":
        invoice["estado"] = "Devuelta SRI"
        invoice["sriEstado"] = reception.get("estado") or "DEVUELTA"
        invoice["sriMensaje"] = "; ".join(m.get("mensaje", "") for m in reception.get("mensajes", [])) or "Comprobante devuelto por el SRI"
        return invoice
    invoice["estado"] = "Recibida SRI"
    invoice["sriEstado"] = "RECIBIDA"
    invoice["sriMensaje"] = "Comprobante recibido; consultando autorizacion"
    last_auth = None
    for _ in range(max(1, SRI_AUTH_RETRIES)):
        last_auth = sri_autorizacion(invoice["claveAcceso"], invoice["sri"]["ambiente"])
        if last_auth.get("estado") in ("AUTORIZADO", "NO AUTORIZADO"):
            break
        time.sleep(max(0.1, SRI_AUTH_SLEEP_SECONDS))
    invoice["sriAutorizacion"] = last_auth or {}
    if last_auth and last_auth.get("estado") == "AUTORIZADO":
        invoice["estado"] = "Autorizado SRI"
        invoice["sriEstado"] = "AUTORIZADO"
        invoice["autorizacion"] = last_auth.get("numeroAutorizacion") or invoice["claveAcceso"]
        invoice["fechaAutorizacion"] = last_auth.get("fechaAutorizacion") or now_iso()
        if last_auth.get("comprobante"):
            invoice["authorizedXml"] = last_auth["comprobante"]
        invoice["sriMensaje"] = "Autorizado por el SRI"
    elif last_auth and last_auth.get("estado") == "NO AUTORIZADO":
        invoice["estado"] = "No autorizado SRI"
        invoice["sriEstado"] = "NO AUTORIZADO"
        invoice["sriMensaje"] = "; ".join(m.get("mensaje", "") for m in last_auth.get("mensajes", [])) or "No autorizado por el SRI"
    else:
        invoice["estado"] = "En proceso SRI"
        invoice["sriEstado"] = "EN_PROCESO"
        invoice["sriMensaje"] = "El SRI aun no devuelve autorizacion; usa Reintentar SRI"
    return invoice


def save_invoice_record(conn, invoice):
    invoices = get_json_key(conn, "facturas", []) or []
    invoices = [f for f in invoices if f.get("id") != invoice.get("id")]
    invoices.insert(0, invoice)
    set_json_key(conn, "facturas", invoices)



def invoice_context(conn, invoice_id):
    invoices = get_json_key(conn, "facturas", []) or []
    invoice = next((f for f in invoices if str(f.get("id")) == str(invoice_id)), None)
    if not invoice:
        raise SRIIntegrationError("Factura no encontrada")
    patients = get_json_key(conn, "pacientes", []) or []
    patient = find_patient(patients, patient_id=int(invoice.get("pac") or 0)) or {}
    config = get_json_key(conn, "config", {}) or {}
    if not invoice.get("sri"):
        invoice["sri"] = sri_config(config)
    if not invoice.get("secuencial"):
        invoice["secuencial"] = clean_digits(invoice.get("id"))[-9:].zfill(9)
    if not invoice.get("xml"):
        invoice["xml"] = build_invoice_xml(invoice, patient, config)
    return invoice, patient, config


def persist_invoice_update(conn, invoice):
    invoices = get_json_key(conn, "facturas", []) or []
    for idx, item in enumerate(invoices):
        if str(item.get("id")) == str(invoice.get("id")):
            invoices[idx] = invoice
            set_json_key(conn, "facturas", invoices)
            return
    invoices.insert(0, invoice)
    set_json_key(conn, "facturas", invoices)
def fix_text(value):
    if isinstance(value, str):
        for bad, good in MOJIBAKE_REPLACEMENTS.items():
            value = value.replace(bad, good)
        return value
    if isinstance(value, list):
        return [fix_text(v) for v in value]
    if isinstance(value, dict):
        return {k: fix_text(v) for k, v in value.items()}
    return value


def get_json_key(conn, key, default=None):
    row = conn.execute("select value from app_data where key = ?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def set_json_key(conn, key, value):
    value = fix_text(value)
    conn.execute(
        "insert into app_data(key,value,updated_at) values(?,?,?) "
        "on conflict(key) do update set value=excluded.value, updated_at=excluded.updated_at",
        (key, json.dumps(value, ensure_ascii=False), now_iso()),
    )


def audit(conn, user, action, key, detail=None):
    conn.execute(
        "insert into audit_log(ts,user_id,email,action,data_key,detail) values(?,?,?,?,?,?)",
        (
            now_iso(),
            user.get("id") if user else None,
            user.get("email") if user else "",
            action,
            key,
            json.dumps(detail or {}, ensure_ascii=False),
        ),
    )


def public_user(user):
    return {
        "id": user.get("id"),
        "name": user.get("name", ""),
        "last": user.get("last", ""),
        "email": user.get("email", ""),
        "rol": user.get("rol", "recepcion"),
        "permissions": clean_permissions(user.get("permissions"), user.get("rol", "recepcion")),
        "patientId": user.get("patientId"),
        "medicoId": user.get("medicoId"),
        "createdAt": user.get("createdAt", ""),
        "estado": user.get("estado", "activo"),
        "emailVerified": user_email_verified(user),
    }


def clean_permissions(permissions, role):
    if role == "admin":
        return sorted(ALLOWED_PERMISSIONS)
    if role == "paciente":
        return []
    if not isinstance(permissions, list) or not permissions:
        permissions = ROLE_DEFAULT_PERMISSIONS.get(role, ROLE_DEFAULT_PERMISSIONS["recepcion"])
    return [p for p in permissions if p in ALLOWED_PERMISSIONS and p != "config"]



def lookup_key(value):
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def resolve_medico_id(conn, payload, name="", last="", email=""):
    medicos = get_json_key(conn, "medicos", []) or []
    raw_id = payload.get("medicoId") or payload.get("medico_id") or payload.get("med")
    if raw_id not in (None, ""):
        try:
            medico_id = int(raw_id)
        except (TypeError, ValueError):
            medico_id = 0
        if medico_id and any(int(m.get("id", 0)) == medico_id for m in medicos):
            return medico_id
        return 0
    email_key = (email or "").strip().lower()
    if email_key:
        match = next((m for m in medicos if (m.get("email") or "").strip().lower() == email_key), None)
        if match:
            return int(match.get("id") or 0)
    wanted = lookup_key(f"{name} {last}")
    if wanted:
        for medico in medicos:
            med_key = lookup_key(medico.get("nombre", ""))
            if wanted in med_key or med_key in wanted:
                return int(medico.get("id") or 0)
    return 0

def can_save_key(user, key):
    role = user.get("rol", "recepcion")
    if role == "admin":
        return True
    if key in ("servicios", "examenes"):
        return False
    perms = set(clean_permissions(user.get("permissions"), role))
    key_map = {
        "citas": "agenda",
        "cajas": "caja",
        "facturas": "facturacion",
        "notas": "hce",
        "recetas": "hce",
        "archivosClinicos": "hce",
        "pacientes": "pacientes",
        "medicos": "medicos",
        "especialidades": "especialidades",
        "seguros": "seguros",
        "quirofanos": "quirofanos",
        "equipos": "quirofanos",
        "stockQx": "quirofanos",
        "servicios": "servicios",
        "examenes": "examenes",
        "cotizaciones": "examenes",
    }
    if key == "pacientes" and ({"agenda", "hce"} & perms):
        return True
    if key == "facturas" and "caja" in perms:
        return True
    if key == "nextIds" and perms:
        return True
    return key in key_map and key_map[key] in perms


def init_db():
    with db() as conn:
        conn.execute(
            "create table if not exists app_data("
            "key text primary key, value text not null, updated_at text not null)"
        )
        conn.execute(table_postgres_audit() if DB_DRIVER == "postgres" else table_sqlite_audit())
        conn.execute(
            "create table if not exists sessions("
            "token_hash text primary key, user_id integer not null, expires_at real not null, created_at text not null)"
        )
        conn.execute("delete from sessions where expires_at < ?", (time.time(),))
        users = get_json_key(conn, "users")
        if not users:
            users = [
                {
                    "id": 1,
                    "name": "Admin",
                    "last": "Sistema",
                    "email": ADMIN_EMAIL,
                    "passHash": hash_password(ADMIN_PASSWORD),
                    "rol": "admin",
                    "permissions": clean_permissions(None, "admin"),
                    "estado": "activo",
                    "emailVerified": True,
                    "createdAt": now_iso(),
                }
            ]
            set_json_key(conn, "users", users)
        else:
            changed = False
            for user in users:
                if user.get("pass") and not user.get("passHash"):
                    user["passHash"] = hash_password(user.pop("pass"))
                    changed = True
                if "emailVerified" not in user:
                    user["emailVerified"] = user.get("estado", "activo") == "activo"
                    changed = True
                cleaned_permissions = clean_permissions(user.get("permissions"), user.get("rol", "recepcion"))
                if user.get("permissions") != cleaned_permissions:
                    user["permissions"] = cleaned_permissions
                    changed = True
                if user.get("rol") == "medico" and not user.get("medicoId"):
                    medico_id = resolve_medico_id(conn, {}, user.get("name", ""), user.get("last", ""), user.get("email", ""))
                    if medico_id:
                        user["medicoId"] = medico_id
                        changed = True
            fixed_users = fix_text(users)
            if fixed_users != users:
                users = fixed_users
                changed = True
            if changed:
                set_json_key(conn, "users", users)
        for row in conn.execute("select key,value from app_data").fetchall():
            value = json.loads(row["value"])
            fixed_value = fix_text(value)
            if fixed_value != value:
                set_json_key(conn, row["key"], fixed_value)
        next_ids = get_json_key(conn, "nextIds")
        if not next_ids:
            set_json_key(conn, "nextIds", {"pac": 6, "med": 5, "cita": 6, "fac": 1845, "esp": 7, "seg": 5, "user": 2, "qx": 3, "eq": 3, "st": 3, "caja": 1, "serv": 6, "exam": 6, "cot": 1})
        else:
            changed_ids = False
            for key, value in {"qx": 3, "eq": 3, "st": 3, "caja": 1, "serv": 6, "exam": 6, "cot": 1}.items():
                if key not in next_ids:
                    next_ids[key] = value
                    changed_ids = True
            if changed_ids:
                set_json_key(conn, "nextIds", next_ids)
        if get_json_key(conn, "archivosClinicos") is None:
            set_json_key(conn, "archivosClinicos", {})
        if get_json_key(conn, "notificaciones") is None:
            set_json_key(conn, "notificaciones", [])
        if get_json_key(conn, "sriCertificate") is None:
            set_json_key(conn, "sriCertificate", {})


def make_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    origin = handler.headers.get("Origin", "")
    if not ALLOWED_ORIGINS or origin in ALLOWED_ORIGINS:
        handler.send_header("Access-Control-Allow-Origin", origin or "*")
    handler.send_header("Vary", "Origin")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("X-Frame-Options", "DENY")
    handler.send_header("Referrer-Policy", "no-referrer")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def make_html_response(handler, status, html):
    body = html.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("X-Frame-Options", "DENY")
    handler.send_header("Referrer-Policy", "no-referrer")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_body(handler):
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length > MAX_BODY_BYTES:
        raise ValueError("payload_too_large")
    return json.loads(handler.rfile.read(length).decode("utf-8") or "{}")


def auth_user(handler):
    token = handler.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if not token:
        return None
    with db() as conn:
        row = conn.execute(
            "select user_id, expires_at from sessions where token_hash = ?",
            (token_hash(token),),
        ).fetchone()
        if not row or row["expires_at"] < time.time():
            if row:
                conn.execute("delete from sessions where token_hash = ?", (token_hash(token),))
            return None
        users = get_json_key(conn, "users", [])
    user = next((u for u in users if int(u.get("id", 0)) == int(row["user_id"])), None)
    if not user or user.get("estado", "activo") != "activo":
        return None
    return user


def split_full_name(value):
    parts = [p for p in (value or "").strip().split() if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]


def next_id(next_ids, key, fallback):
    current = int(next_ids.get(key, fallback) or fallback)
    next_ids[key] = current + 1
    return current


def find_patient(patients, email="", cedula="", patient_id=0):
    email = (email or "").strip().lower()
    cedula = (cedula or "").strip()
    for patient in patients:
        if patient_id and int(patient.get("id", 0)) == int(patient_id):
            return patient
        if cedula and (patient.get("cedula") or "").strip() == cedula:
            return patient
        if email and (patient.get("email") or "").strip().lower() == email:
            return patient
    return None


def upsert_patient_from_payload(conn, payload):
    patients = get_json_key(conn, "pacientes", []) or []
    next_ids = get_json_key(conn, "nextIds", {}) or {}
    email = (payload.get("email") or "").strip().lower()
    cedula = (payload.get("cedula") or payload.get("documento") or "").strip()
    name = (payload.get("name") or payload.get("nombres") or "").strip()
    last = (payload.get("last") or payload.get("apellidos") or "").strip()
    full_name = (payload.get("nombreCompleto") or payload.get("paciente") or "").strip()
    if not name and full_name:
        name, last = split_full_name(full_name)
    patient = find_patient(patients, email=email, cedula=cedula)
    created = False
    if not patient:
        patient = {
            "id": next_id(next_ids, "pac", len(patients) + 1),
            "nombres": name,
            "apellidos": last,
            "cedula": cedula,
            "fnac": payload.get("fnac") or "",
            "genero": payload.get("genero") or "",
            "tel": payload.get("tel") or payload.get("phone") or "",
            "email": email,
            "dir": payload.get("dir") or "",
            "seguro": payload.get("seguro") or "",
            "afiliado": payload.get("afiliado") or "",
            "sangre": payload.get("sangre") or "",
            "alergias": payload.get("alergias") or "",
            "antec": payload.get("antec") or "",
            "esp": payload.get("esp") or payload.get("especialidad") or "",
            "ultima": "",
            "origen": payload.get("origen") or "Landing pÃºblica",
            "createdAt": now_iso(),
        }
        patients.append(patient)
        created = True
    else:
        updates = {
            "nombres": name,
            "apellidos": last,
            "cedula": cedula,
            "fnac": payload.get("fnac") or "",
            "genero": payload.get("genero") or "",
            "tel": payload.get("tel") or payload.get("phone") or "",
            "email": email,
            "dir": payload.get("dir") or "",
            "seguro": payload.get("seguro") or "",
            "afiliado": payload.get("afiliado") or "",
            "sangre": payload.get("sangre") or "",
            "alergias": payload.get("alergias") or "",
            "antec": payload.get("antec") or "",
            "esp": payload.get("esp") or payload.get("especialidad") or "",
        }
        for key, value in updates.items():
            if value and not patient.get(key):
                patient[key] = value
    set_json_key(conn, "pacientes", patients)
    set_json_key(conn, "nextIds", next_ids)
    return patient, created


def create_online_appointment(conn, patient, payload, user=None):
    appointments = get_json_key(conn, "citas", []) or []
    medicos = get_json_key(conn, "medicos", []) or []
    next_ids = get_json_key(conn, "nextIds", {}) or {}
    esp = (payload.get("esp") or payload.get("especialidad") or patient.get("esp") or "").strip()
    med = int(payload.get("med") or payload.get("medicoId") or 0)
    if not med and esp:
        doctor = next((m for m in medicos if (m.get("esp") or "") == esp), None)
        med = int(doctor.get("id", 0)) if doctor else 0
    appointment = {
        "id": next_id(next_ids, "cita", len(appointments) + 1),
        "pac": int(patient.get("id")),
        "med": med,
        "esp": esp,
        "tipo": payload.get("tipo") or "Reserva online",
        "fecha": payload.get("fecha") or "",
        "hora": payload.get("hora") or "08:00",
        "motivo": payload.get("motivo") or "",
        "estado": "Solicitada online",
        "notif": "Sistema",
        "origen": payload.get("origen") or "Landing pÃºblica",
        "createdAt": now_iso(),
        "createdBy": user.get("email") if user else "paciente-web",
    }
    appointments.append(appointment)
    set_json_key(conn, "citas", appointments)
    set_json_key(conn, "nextIds", next_ids)
    notifications = get_json_key(conn, "notificaciones", []) or []
    notifications.insert(0, {
        "id": f"web-{appointment['id']}",
        "tipo": "cita_online",
        "fecha": now_iso(),
        "titulo": "Nueva cita solicitada desde la landing",
        "detalle": f"{patient.get('nombres', '')} {patient.get('apellidos', '')} pidiÃ³ cita de {esp} el {appointment['fecha']} a las {appointment['hora']}",
        "citaId": appointment["id"],
        "leida": False,
    })
    set_json_key(conn, "notificaciones", notifications[:80])
    return appointment


def patient_portal_payload(conn, user):
    patients = get_json_key(conn, "pacientes", []) or []
    patient = find_patient(
        patients,
        email=user.get("email", ""),
        patient_id=int(user.get("patientId") or 0),
    )
    if not patient:
        return None
    patient_id = int(patient.get("id"))
    appointments = [c for c in (get_json_key(conn, "citas", []) or []) if int(c.get("pac", 0)) == patient_id]
    notes = (get_json_key(conn, "notas", {}) or {}).get(str(patient_id), []) or (get_json_key(conn, "notas", {}) or {}).get(patient_id, []) or []
    prescriptions = (get_json_key(conn, "recetas", {}) or {}).get(str(patient_id), []) or (get_json_key(conn, "recetas", {}) or {}).get(patient_id, []) or []
    files = (get_json_key(conn, "archivosClinicos", {}) or {}).get(str(patient_id), []) or (get_json_key(conn, "archivosClinicos", {}) or {}).get(patient_id, []) or []
    invoices = [f for f in (get_json_key(conn, "facturas", []) or []) if int(f.get("pac", 0)) == patient_id]
    return {
        "patient": patient,
        "appointments": sorted(appointments, key=lambda c: (c.get("fecha", ""), c.get("hora", "")), reverse=True),
        "notes": sorted(notes, key=lambda n: n.get("fecha", ""), reverse=True),
        "prescriptions": sorted(prescriptions, key=lambda r: r.get("fecha", ""), reverse=True),
        "files": sorted(files, key=lambda f: f.get("fecha", ""), reverse=True),
        "invoices": sorted(invoices, key=lambda f: f.get("fecha", ""), reverse=True),
    }


def public_catalog_payload(conn):
    config = get_json_key(conn, "config", {}) or {}
    public_config = {k: config.get(k, "") for k in ("nombre", "dir", "tel", "wa", "email", "color", "logo")}
    return {
        "config": public_config,
        "especialidades": [e for e in (get_json_key(conn, "especialidades", []) or []) if e.get("estado", "activo") == "activo"],
        "medicos": get_json_key(conn, "medicos", []) or [],
        "servicios": get_json_key(conn, "servicios", []) or [],
    }


def sanitize_app_data_for_user(data, user=None):
    data = dict(data or {})
    saved_cert = data.pop("sriCertificate", None)
    config = data.get("config") or {}
    if isinstance(config, dict):
        config = dict(config)
        for secret_key in ("sriCertP12Base64", "sriCertPassword", "sriCertificate", "sriCertificatePassword"):
            config.pop(secret_key, None)
        data["config"] = config
    data["users"] = [public_user(u) for u in data.get("users", [])]
    data["sriCertificateStatus"] = saved_sri_certificate_status(saved_cert)
    return data


class MedicGHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".txt": "text/plain; charset=utf-8",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/health", "/api/health"):
            return make_response(self, 200, {"ok": True, "db": DB_DRIVER})
        if path == "/api/public/options":
            with db() as conn:
                return make_response(self, 200, public_catalog_payload(conn))
        if path == "/api/verify-email":
            token = parse_qs(urlparse(self.path).query).get("token", [""])[0]
            if not token:
                return make_html_response(self, 400, "<h1>Enlace invÃ¡lido</h1><p>Falta el token de verificaciÃ³n.</p>")
            hashed_token = token_hash(token)
            with db() as conn:
                users = get_json_key(conn, "users", [])
                target = next((u for u in users if u.get("verifyTokenHash") == hashed_token), None)
                if not target:
                    return make_html_response(self, 404, "<h1>Enlace no encontrado</h1><p>Solicita un nuevo registro o contacta al administrador.</p>")
                if float(target.get("verifyExpiresAt") or 0) < time.time():
                    return make_html_response(self, 410, "<h1>Enlace expirado</h1><p>RegÃ­strate nuevamente para recibir otro correo de verificaciÃ³n.</p>")
                target["emailVerified"] = True
                target["estado"] = "activo"
                target.pop("verifyTokenHash", None)
                target.pop("verifyExpiresAt", None)
                set_json_key(conn, "users", users)
                audit(conn, target, "verify_email", "users")
            return make_html_response(
                self,
                200,
                "<!doctype html><html lang='es'><meta charset='utf-8'>"
                "<title>Cuenta verificada</title>"
                "<body style='font-family:Arial,sans-serif;padding:32px;color:#1f2937;'>"
                "<h1>Correo verificado correctamente</h1>"
                "<p>Ya puedes iniciar sesiÃ³n en Medic G. Si todavÃ­a no ves mÃ³dulos, el administrador debe asignarte permisos.</p>"
                "<p><a href='/' style='color:#0d7a6b;font-weight:700;'>Ir al sistema</a></p>"
                "</body></html>",
            )
        if path == "/api/data":
            user = auth_user(self)
            if not user:
                return make_response(self, 401, {"error": "SesiÃ³n no vÃ¡lida"})
            if user.get("rol") == "paciente":
                return make_response(self, 403, {"error": "Usa el portal del paciente"})
            with db() as conn:
                rows = conn.execute("select key,value from app_data").fetchall()
            data = {row["key"]: json.loads(row["value"]) for row in rows}
            data = sanitize_app_data_for_user(data, user)
            return make_response(self, 200, {"user": public_user(user), "data": data})
        if path == "/api/patient/portal":
            user = auth_user(self)
            if not user:
                return make_response(self, 401, {"error": "SesiÃ³n no vÃ¡lida"})
            if user.get("rol") != "paciente":
                return make_response(self, 403, {"error": "Portal disponible solo para pacientes"})
            with db() as conn:
                portal = patient_portal_payload(conn, user)
            if not portal:
                return make_response(self, 404, {"error": "No encontramos una ficha de paciente vinculada a tu correo"})
            return make_response(self, 200, {"user": public_user(user), "portal": portal})
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = read_body(self)
        except ValueError as exc:
            if str(exc) == "payload_too_large":
                return make_response(self, 413, {"error": "Archivo o solicitud demasiado grande"})
            return make_response(self, 400, {"error": "JSON invÃ¡lido"})
        except Exception:
            return make_response(self, 400, {"error": "JSON invÃ¡lido"})

        if path == "/api/login":
            email = (payload.get("email") or "").strip().lower()
            password = payload.get("password") or ""
            with db() as conn:
                users = get_json_key(conn, "users", [])
            user = next((u for u in users if (u.get("email") or "").lower() == email), None)
            if not user or not verify_password(password, user.get("passHash") or user.get("pass")):
                return make_response(self, 401, {"error": "Correo o contraseÃ±a incorrectos"})
            if not user_email_verified(user) or user.get("estado") == "pendiente_verificacion":
                return make_response(self, 403, {"error": "Verifica tu correo electrÃ³nico antes de iniciar sesiÃ³n"})
            if user.get("estado", "activo") != "activo":
                return make_response(self, 403, {"error": "Usuario no activo"})
            token = secrets.token_urlsafe(32)
            expires_at = time.time() + 24 * 3600
            with db() as conn:
                conn.execute(
                    "insert into sessions(token_hash,user_id,expires_at,created_at) values(?,?,?,?)",
                    (token_hash(token), user["id"], expires_at, now_iso()),
                )
                audit(conn, user, "login", "session")
            return make_response(self, 200, {"token": token, "user": public_user(user)})

        if path == "/api/resend-verification":
            email = (payload.get("email") or "").strip().lower()
            if not email:
                return make_response(self, 400, {"error": "Ingresa el correo registrado"})
            verify_token = secrets.token_urlsafe(32)
            verify_link = f"{app_base_url(self)}/api/verify-email?token={verify_token}"
            target_name = "Paciente"
            with db() as conn:
                users = get_json_key(conn, "users", [])
                target = next((u for u in users if (u.get("email") or "").lower() == email), None)
                if not target:
                    audit(conn, None, "resend_verification_unknown_email", "users", {"email": email})
                    return make_response(self, 200, {
                        "ok": True,
                        "emailSent": False,
                        "message": "Si el correo esta registrado, enviaremos un nuevo enlace de verificacion.",
                    })
                if user_email_verified(target) and target.get("estado") != "pendiente_verificacion":
                    return make_response(self, 200, {
                        "ok": True,
                        "emailSent": False,
                        "alreadyVerified": True,
                        "message": "Este correo ya esta verificado. Intenta iniciar sesion.",
                    })
                target["emailVerified"] = False
                target["estado"] = "pendiente_verificacion"
                target["verifyTokenHash"] = token_hash(verify_token)
                target["verifyExpiresAt"] = time.time() + 48 * 3600
                target_name = target.get("name") or target.get("nombres") or "Paciente"
                set_json_key(conn, "users", users)
                audit(conn, None, "resend_verification_requested", "users", {"email": email})
            email_sent, email_error = send_verification_email(email, target_name, verify_link)
            with db() as conn:
                audit(conn, None, "resend_verification_sent" if email_sent else "resend_verification_failed", "users", {
                    "email": email,
                    "sent": email_sent,
                    "error": email_error if not email_sent else "",
                })
            response = {
                "ok": True,
                "emailSent": email_sent,
                "message": "Te enviamos un nuevo correo de verificacion. Revisa tambien spam o promociones." if email_sent else "No se pudo enviar el correo. Revisa SMTP/Resend en Vercel y vuelve a intentar.",
            }
            if not email_sent:
                response["emailError"] = email_error
            if SHOW_VERIFICATION_LINK:
                response["verificationLink"] = verify_link
            return make_response(self, 200, response)
        if path == "/api/register":
            name = (payload.get("name") or "").strip()
            last = (payload.get("last") or "").strip()
            email = (payload.get("email") or "").strip().lower()
            password = payload.get("password") or ""
            if not name or not last or not email or len(password) < 6:
                return make_response(self, 400, {"error": "Completa nombre, apellido, correo y contraseÃ±a de mÃ­nimo 6 caracteres"})
            verify_token = secrets.token_urlsafe(32)
            verify_link = f"{app_base_url(self)}/api/verify-email?token={verify_token}"
            with db() as conn:
                users = get_json_key(conn, "users", [])
                if any((u.get("email") or "").lower() == email for u in users):
                    return make_response(self, 409, {"error": "Este correo ya estÃ¡ registrado"})
                patient, _ = upsert_patient_from_payload(conn, {
                    **payload,
                    "name": name,
                    "last": last,
                    "email": email,
                    "origen": "Registro web",
                })
                next_ids = get_json_key(conn, "nextIds", {})
                new_id = next_id(next_ids, "user", len(users) + 1)
                new_user = {
                    "id": new_id,
                    "name": name,
                    "last": last,
                    "email": email,
                    "passHash": hash_password(password),
                    "rol": "paciente",
                    "permissions": [],
                    "estado": "pendiente_verificacion",
                    "emailVerified": False,
                    "patientId": patient.get("id"),
                    "verifyTokenHash": token_hash(verify_token),
                    "verifyExpiresAt": time.time() + 48 * 3600,
                    "createdAt": now_iso(),
                }
                users.append(new_user)
                set_json_key(conn, "users", users)
                set_json_key(conn, "nextIds", next_ids)
                audit(conn, None, "patient_register", "users", {"createdUserId": new_id, "createdEmail": email, "patientId": patient.get("id")})
            try:
                email_sent, email_error = send_verification_email(email, name, verify_link)
            except Exception as exc:
                email_sent, email_error = False, str(exc)
            response = {
                "ok": True,
                "emailSent": email_sent,
                "message": "Cuenta creada. Revisa tu correo para verificar tu cuenta antes de iniciar sesiÃ³n.",
            }
            if not email_sent:
                response["message"] = "Cuenta creada, pero el servidor de correo no estÃ¡ configurado. Configura SMTP o Resend para enviar verificaciones."
                response["emailError"] = email_error
            if SHOW_VERIFICATION_LINK:
                response["verificationLink"] = verify_link
            return make_response(self, 201, response)

        if path == "/api/public/appointment":
            required = [
                payload.get("name") or payload.get("nombres") or payload.get("paciente"),
                payload.get("last") or payload.get("apellidos") or payload.get("paciente"),
                payload.get("email"),
                payload.get("tel") or payload.get("phone"),
                payload.get("esp") or payload.get("especialidad"),
                payload.get("fecha"),
                payload.get("hora"),
            ]
            if any(not str(v or "").strip() for v in required):
                return make_response(self, 400, {"error": "Completa paciente, correo, telÃ©fono, especialidad, fecha y hora"})
            with db() as conn:
                patient, patient_created = upsert_patient_from_payload(conn, {**payload, "origen": "Landing pÃºblica"})
                appointment = create_online_appointment(conn, patient, payload)
                audit(conn, None, "public_appointment", "citas", {"appointmentId": appointment["id"], "patientId": patient.get("id")})
            return make_response(self, 201, {
                "ok": True,
                "patientCreated": patient_created,
                "appointment": appointment,
                "message": "Cita solicitada correctamente. El centro mÃ©dico la verÃ¡ en agenda y te confirmarÃ¡ la atenciÃ³n.",
            })

        if path == "/api/logout":
            token = self.headers.get("Authorization", "").replace("Bearer ", "").strip()
            user = auth_user(self)
            with db() as conn:
                if user:
                    audit(conn, user, "logout", "session")
                if token:
                    conn.execute("delete from sessions where token_hash = ?", (token_hash(token),))
            return make_response(self, 200, {"ok": True})

        user = auth_user(self)
        if not user:
            return make_response(self, 401, {"error": "SesiÃ³n no vÃ¡lida"})

        if path == "/api/sri/certificate":
            if user.get("rol") != "admin":
                return make_response(self, 403, {"error": "Solo el dueno/administrador puede configurar el certificado SRI"})
            action = (payload.get("action") or "save").strip().lower()
            with db() as conn:
                if action == "status":
                    return make_response(self, 200, {"ok": True, "status": sri_certificate_status(conn)})
                if action == "delete":
                    if SRI_CERT_P12_BASE64:
                        return make_response(self, 400, {"error": "El certificado viene de variables privadas de Vercel. Eliminalo desde Vercel si deseas cambiarlo."})
                    set_json_key(conn, "sriCertificate", {})
                    audit(conn, user, "delete_sri_certificate", "sriCertificate")
                    return make_response(self, 200, {"ok": True, "status": sri_certificate_status(conn)})
                cert_b64 = normalize_cert_base64(payload.get("p12Base64") or payload.get("certificate") or "")
                password = str(payload.get("password") or "")
                filename = str(payload.get("filename") or "certificado-sri.p12")[:160]
                if not cert_b64:
                    return make_response(self, 400, {"error": "Selecciona el archivo .p12 o .pfx del certificado digital"})
                if not password:
                    return make_response(self, 400, {"error": "Ingresa la clave del certificado digital"})
                try:
                    base64.b64decode(cert_b64, validate=True)
                except Exception:
                    return make_response(self, 400, {"error": "No se pudo leer el certificado. Sube un archivo .p12/.pfx valido."})
                set_json_key(conn, "sriCertificate", {
                    "p12Base64": cert_b64,
                    "password": password,
                    "filename": filename,
                    "updatedAt": now_iso(),
                    "uploadedBy": user.get("email", ""),
                })
                audit(conn, user, "save_sri_certificate", "sriCertificate", {"filename": filename})
                return make_response(self, 200, {"ok": True, "status": sri_certificate_status(conn)})
        if path == "/api/invoices":
            if not can_invoice_sri(user):
                return make_response(self, 403, {"error": "No tienes permiso para emitir facturas"})
            try:
                with db() as conn:
                    invoice, patient, config = prepare_invoice_from_payload(conn, user, payload)
                    cert_info = get_sri_certificate(conn)
                    try:
                        if invoice.get("sri", {}).get("autoSend") and payload.get("sendSri", True):
                            invoice = send_invoice_to_sri(invoice, cert_info)
                        else:
                            invoice["estado"] = "Pendiente SRI"
                            invoice["sriEstado"] = "GENERADO"
                            invoice["sriMensaje"] = "XML generado; envio SRI pendiente"
                    except SRIIntegrationError as exc:
                        invoice["estado"] = "Error SRI"
                        invoice["sriEstado"] = "ERROR"
                        invoice["sriMensaje"] = str(exc)
                    email_sent = False
                    email_error = ""
                    if invoice.get("estado") == "Autorizado SRI" and invoice.get("emailAuto", True):
                        email_sent, email_error = send_invoice_email(invoice, patient, config)
                        invoice["emailEnviado"] = email_sent
                        invoice["emailError"] = email_error
                    save_invoice_record(conn, invoice)
                    audit(conn, user, "sri_invoice_emit", "facturas", {"invoiceId": invoice.get("id"), "estado": invoice.get("estado"), "emailSent": email_sent})
                return make_response(self, 201, {"ok": True, "invoice": invoice, "emailSent": email_sent, "emailError": email_error})
            except SRIIntegrationError as exc:
                return make_response(self, 400, {"error": str(exc)})
            except Exception as exc:
                return make_response(self, 500, {"error": f"No se pudo emitir la factura: {exc}"})

        if path == "/api/invoices/sri-retry":
            if not can_invoice_sri(user):
                return make_response(self, 403, {"error": "No tienes permiso para reenviar facturas al SRI"})
            invoice_id = payload.get("id") or payload.get("invoiceId")
            if not invoice_id:
                return make_response(self, 400, {"error": "Falta el numero de factura"})
            try:
                with db() as conn:
                    invoice, patient, config = invoice_context(conn, invoice_id)
                    cert_info = get_sri_certificate(conn)
                    try:
                        invoice = send_invoice_to_sri(invoice, cert_info)
                    except SRIIntegrationError as exc:
                        invoice["estado"] = "Error SRI"
                        invoice["sriEstado"] = "ERROR"
                        invoice["sriMensaje"] = str(exc)
                    email_sent = False
                    email_error = ""
                    if invoice.get("estado") == "Autorizado SRI" and payload.get("emailAuto", invoice.get("emailAuto", True)):
                        email_sent, email_error = send_invoice_email(invoice, patient, config)
                        invoice["emailEnviado"] = email_sent
                        invoice["emailError"] = email_error
                    persist_invoice_update(conn, invoice)
                    audit(conn, user, "sri_invoice_retry", "facturas", {"invoiceId": invoice.get("id"), "estado": invoice.get("estado"), "emailSent": email_sent})
                return make_response(self, 200, {"ok": True, "invoice": invoice, "emailSent": email_sent, "emailError": email_error})
            except SRIIntegrationError as exc:
                return make_response(self, 404, {"error": str(exc)})
            except Exception as exc:
                return make_response(self, 500, {"error": f"No se pudo consultar el SRI: {exc}"})

        if path == "/api/invoices/email":
            if not can_invoice_sri(user):
                return make_response(self, 403, {"error": "No tienes permiso para enviar facturas por correo"})
            invoice_id = payload.get("id") or payload.get("invoiceId")
            if not invoice_id:
                return make_response(self, 400, {"error": "Falta el numero de factura"})
            try:
                with db() as conn:
                    invoice, patient, config = invoice_context(conn, invoice_id)
                    email_sent, email_error = send_invoice_email(invoice, patient, config)
                    invoice["emailEnviado"] = email_sent
                    invoice["emailError"] = email_error
                    persist_invoice_update(conn, invoice)
                    audit(conn, user, "sri_invoice_email", "facturas", {"invoiceId": invoice.get("id"), "emailSent": email_sent, "error": email_error})
                if not email_sent:
                    return make_response(self, 400, {"error": email_error or "No se pudo enviar el correo", "invoice": invoice})
                return make_response(self, 200, {"ok": True, "invoice": invoice, "emailSent": True})
            except SRIIntegrationError as exc:
                return make_response(self, 404, {"error": str(exc)})

        if path == "/api/invoices/ride":
            if not can_invoice_sri(user) and user.get("rol") != "paciente":
                return make_response(self, 403, {"error": "No tienes permiso para imprimir RIDE"})
            invoice_id = payload.get("id") or payload.get("invoiceId")
            if not invoice_id:
                return make_response(self, 400, {"error": "Falta el numero de factura"})
            try:
                with db() as conn:
                    invoice, patient, config = invoice_context(conn, invoice_id)
                    if user.get("rol") == "paciente" and int(invoice.get("pac") or 0) != int(user.get("patientId") or 0):
                        return make_response(self, 403, {"error": "No puedes ver esta factura"})
                html = ride_html(invoice, patient, config, ticket=(payload.get("format") == "ticket"))
                return make_response(self, 200, {"ok": True, "html": html, "filename": f"RIDE-{invoice.get('id')}.html"})
            except SRIIntegrationError as exc:
                return make_response(self, 404, {"error": str(exc)})

        if path == "/api/invoices/xml":
            if not can_invoice_sri(user) and user.get("rol") != "paciente":
                return make_response(self, 403, {"error": "No tienes permiso para descargar XML"})
            invoice_id = payload.get("id") or payload.get("invoiceId")
            if not invoice_id:
                return make_response(self, 400, {"error": "Falta el numero de factura"})
            try:
                with db() as conn:
                    invoice, _patient, _config = invoice_context(conn, invoice_id)
                    if user.get("rol") == "paciente" and int(invoice.get("pac") or 0) != int(user.get("patientId") or 0):
                        return make_response(self, 403, {"error": "No puedes ver esta factura"})
                xml = invoice.get("authorizedXml") or invoice.get("signedXml") or invoice.get("xml") or ""
                return make_response(self, 200, {"ok": True, "xml": xml, "filename": f"{invoice.get('id')}.xml", "authorized": invoice.get("estado") == "Autorizado SRI"})
            except SRIIntegrationError as exc:
                return make_response(self, 404, {"error": str(exc)})
        if path == "/api/patient/appointment":
            if user.get("rol") != "paciente":
                return make_response(self, 403, {"error": "Ruta disponible solo para pacientes"})
            if not (payload.get("esp") or payload.get("especialidad")) or not payload.get("fecha") or not payload.get("hora"):
                return make_response(self, 400, {"error": "Selecciona especialidad, fecha y hora"})
            with db() as conn:
                portal = patient_portal_payload(conn, user)
                if not portal:
                    return make_response(self, 404, {"error": "No encontramos una ficha de paciente vinculada a tu usuario"})
                appointment = create_online_appointment(conn, portal["patient"], {**payload, "origen": "Portal paciente"}, user)
                audit(conn, user, "patient_appointment", "citas", {"appointmentId": appointment["id"], "patientId": portal["patient"].get("id")})
                portal = patient_portal_payload(conn, user)
            return make_response(self, 201, {"ok": True, "appointment": appointment, "portal": portal})

        if path == "/api/data":
            key = payload.get("key")
            value = payload.get("value")
            if not key:
                return make_response(self, 400, {"error": "Falta key"})
            if key == "users" and user.get("rol") != "admin":
                return make_response(self, 403, {"error": "Solo el administrador puede modificar usuarios"})
            if key != "users" and not can_save_key(user, key):
                return make_response(self, 403, {"error": "No tienes permiso para guardar este mÃ³dulo"})
            with db() as conn:
                set_json_key(conn, key, value)
                audit(conn, user, "save", key)
            return make_response(self, 200, {"ok": True})

        if path == "/api/users":
            if user.get("rol") != "admin":
                return make_response(self, 403, {"error": "Solo el administrador puede crear usuarios"})
            action = payload.get("action") or "create"
            if action in ("update", "delete", "verify"):
                user_id = int(payload.get("userId") or 0)
                with db() as conn:
                    users = get_json_key(conn, "users", [])
                    target = next((u for u in users if int(u.get("id", 0)) == user_id), None)
                    if not target:
                        return make_response(self, 404, {"error": "Usuario no encontrado"})
                    is_self = int(user.get("id", 0)) == user_id
                    admin_count = sum(1 for u in users if u.get("rol") == "admin")

                    if action == "verify":
                        target["emailVerified"] = True
                        target["estado"] = "activo"
                        target.pop("verifyTokenHash", None)
                        target.pop("verifyExpiresAt", None)
                        set_json_key(conn, "users", users)
                        audit(conn, user, "verify_user", "users", {"targetUserId": user_id, "email": target.get("email")})
                        return make_response(self, 200, {"user": public_user(target)})

                    if action == "delete":
                        if is_self:
                            return make_response(self, 400, {"error": "No puedes eliminar tu propio usuario administrador"})
                        if target.get("rol") == "admin" and admin_count <= 1:
                            return make_response(self, 400, {"error": "No puedes eliminar el ultimo administrador"})
                        users = [u for u in users if int(u.get("id", 0)) != user_id]
                        set_json_key(conn, "users", users)
                        conn.execute("delete from sessions where user_id = ?", (user_id,))
                        audit(conn, user, "delete_user", "users", {"targetUserId": user_id, "email": target.get("email"), "rol": target.get("rol")})
                        return make_response(self, 200, {"ok": True, "deletedUserId": user_id})

                    allowed_roles = set(ROLE_DEFAULT_PERMISSIONS.keys())
                    name = (payload.get("name") or "").strip()
                    last = (payload.get("last") or "").strip()
                    email = (payload.get("email") or "").strip().lower()
                    rol = (payload.get("rol") or target.get("rol") or "recepcion").strip()
                    estado = (payload.get("estado") or target.get("estado") or "activo").strip()
                    password = payload.get("password") or ""
                    if not name or not last or not email:
                        return make_response(self, 400, {"error": "Completa nombre, apellido y correo"})
                    if rol not in allowed_roles:
                        return make_response(self, 400, {"error": "Rol no valido"})
                    if any((u.get("email") or "").lower() == email and int(u.get("id", 0)) != user_id for u in users):
                        return make_response(self, 409, {"error": "Este correo ya esta registrado"})
                    if is_self and rol != "admin":
                        return make_response(self, 400, {"error": "No puedes quitarte el rol de administrador"})
                    if target.get("rol") == "admin" and rol != "admin" and admin_count <= 1:
                        return make_response(self, 400, {"error": "Debe quedar al menos un administrador"})
                    if is_self:
                        estado = "activo"
                    if password:
                        if len(password) < 6:
                            return make_response(self, 400, {"error": "La nueva contrasena debe tener minimo 6 caracteres"})
                        target["passHash"] = hash_password(password)
                        target.pop("pass", None)
                    if rol == "paciente" and not target.get("patientId"):
                        patient, _ = upsert_patient_from_payload(conn, {
                            "name": name,
                            "last": last,
                            "email": email,
                            "origen": "Vinculado por administrador",
                        })
                        target["patientId"] = patient.get("id")
                    if rol == "medico":
                        medico_id = resolve_medico_id(conn, payload, name, last, email)
                        if not medico_id:
                            return make_response(self, 400, {"error": "Selecciona el perfil medico vinculado para este usuario"})
                        target["medicoId"] = medico_id
                    else:
                        target.pop("medicoId", None)
                    if rol != "paciente":
                        target.pop("patientId", None)
                    target.update({
                        "name": name,
                        "last": last,
                        "email": email,
                        "rol": rol,
                        "estado": estado,
                        "permissions": clean_permissions(payload.get("permissions"), rol),
                        "updatedAt": now_iso(),
                    })
                    set_json_key(conn, "users", users)
                    audit(conn, user, "update_user", "users", {"targetUserId": user_id, "email": email, "rol": rol, "estado": estado})
                    return make_response(self, 200, {"user": public_user(target)})
            if payload.get("action") == "permissions":
                user_id = int(payload.get("userId") or 0)
                permissions = payload.get("permissions") or []
                with db() as conn:
                    users = get_json_key(conn, "users", [])
                    target = next((u for u in users if int(u.get("id", 0)) == user_id), None)
                    if not target:
                        return make_response(self, 404, {"error": "Usuario no encontrado"})
                    target["permissions"] = clean_permissions(permissions, target.get("rol", "recepcion"))
                    set_json_key(conn, "users", users)
                    audit(conn, user, "update_permissions", "users", {"targetUserId": user_id, "permissions": target["permissions"]})
                return make_response(self, 200, {"user": public_user(target)})
            name = (payload.get("name") or "").strip()
            last = (payload.get("last") or "").strip()
            email = (payload.get("email") or "").strip().lower()
            password = payload.get("password") or ""
            rol = payload.get("rol") or "recepcion"
            if not name or not last or not email or len(password) < 6:
                return make_response(self, 400, {"error": "Completa nombre, apellido, correo y contraseÃ±a de mÃ­nimo 6 caracteres"})
            permissions = clean_permissions(payload.get("permissions"), rol)
            with db() as conn:
                users = get_json_key(conn, "users", [])
                if any((u.get("email") or "").lower() == email for u in users):
                    return make_response(self, 409, {"error": "Este correo ya estÃ¡ registrado"})
                if rol not in ROLE_DEFAULT_PERMISSIONS:
                    return make_response(self, 400, {"error": "Rol no valido"})
                patient_id = None
                medico_id = None
                if rol == "paciente":
                    patient, _ = upsert_patient_from_payload(conn, {
                        "name": name,
                        "last": last,
                        "email": email,
                        "origen": "Creado por administrador",
                    })
                    patient_id = patient.get("id")
                if rol == "medico":
                    medico_id = resolve_medico_id(conn, payload, name, last, email)
                    if not medico_id:
                        return make_response(self, 400, {"error": "Selecciona el perfil medico vinculado para este usuario"})
                next_ids = get_json_key(conn, "nextIds", {})
                new_id = int(next_ids.get("user", len(users) + 1))
                next_ids["user"] = new_id + 1
                new_user = {
                    "id": new_id,
                    "name": name,
                    "last": last,
                    "email": email,
                    "passHash": hash_password(password),
                    "rol": rol,
                    "permissions": permissions,
                    "estado": "activo",
                    "emailVerified": True,
                    "patientId": patient_id,
                    "medicoId": medico_id,
                    "createdAt": now_iso(),
                }
                users.append(new_user)
                set_json_key(conn, "users", users)
                set_json_key(conn, "nextIds", next_ids)
                audit(conn, user, "create_user", "users", {"createdUserId": new_id, "createdEmail": email, "rol": rol})
            return make_response(self, 200, {"user": public_user(new_user)})

        if path == "/api/users/permissions":
            if user.get("rol") != "admin":
                return make_response(self, 403, {"error": "Solo el administrador puede configurar permisos"})
            user_id = int(payload.get("userId") or 0)
            permissions = payload.get("permissions") or []
            with db() as conn:
                users = get_json_key(conn, "users", [])
                target = next((u for u in users if int(u.get("id", 0)) == user_id), None)
                if not target:
                    return make_response(self, 404, {"error": "Usuario no encontrado"})
                target["permissions"] = clean_permissions(permissions, target.get("rol", "recepcion"))
                set_json_key(conn, "users", users)
                audit(conn, user, "update_permissions", "users", {"targetUserId": user_id, "permissions": target["permissions"]})
            return make_response(self, 200, {"user": public_user(target)})

        return make_response(self, 404, {"error": "Ruta no encontrada"})

    def do_OPTIONS(self):
        return make_response(self, 200, {"ok": True})


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), MedicGHandler)
    print(f"Medic G con base de datos {DB_DRIVER}")
    print(f"Abre: http://{HOST}:{PORT}")
    print(f"Base de datos: {DB_PATH if DB_DRIVER == 'sqlite' else 'PostgreSQL'}")
    server.serve_forever()












