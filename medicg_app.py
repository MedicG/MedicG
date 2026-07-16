from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from email.message import EmailMessage
from email.utils import formataddr
import hashlib
import json
import os
import secrets
import smtplib
import sqlite3
import time
import urllib.error
import urllib.request

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
    "GestiÃ³n": "Gestión",
    "MÃ©dica": "Médica",
    "MÃ©dicas": "Médicas",
    "MÃ©dico": "Médico",
    "mÃ©dico": "médico",
    "mÃ©dicos": "médicos",
    "ClÃ­nica": "Clínica",
    "ElectrÃ³nica": "Electrónica",
    "FacturaciÃ³n": "Facturación",
    "estadÃ­sticas": "estadísticas",
    "sesiÃ³n": "sesión",
    "SesiÃ³n": "Sesión",
    "electrÃ³nico": "electrónico",
    "ContraseÃ±a": "Contraseña",
    "contraseÃ±a": "contraseña",
    "RecepciÃ³n": "Recepción",
    "ConfiguraciÃ³n": "Configuración",
    "dÃ­a": "día",
    "PediatrÃ­a": "Pediatría",
    "CardiologÃ­a": "Cardiología",
    "DermatologÃ­a": "Dermatología",
    "NeurologÃ­a": "Neurología",
    "PÃ©rez": "Pérez",
    "PÃºblico": "Público",
    "MarÃ­a": "María",
    "MuÃ±oz": "Muñoz",
    "IbÃ¡Ã±ez": "Ibáñez",
    "RÃ­os": "Ríos",
    "cirugÃ­as": "cirugías",
    "atenciÃ³n": "atención",
    "corazÃ³n": "corazón",
    "fÃ­sica": "física",
    "DiagnÃ³stico": "Diagnóstico",
    "MÃ­n.": "Mín.",
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
            "origen": payload.get("origen") or "Landing pública",
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
        "origen": payload.get("origen") or "Landing pública",
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
        "detalle": f"{patient.get('nombres', '')} {patient.get('apellidos', '')} pidió cita de {esp} el {appointment['fecha']} a las {appointment['hora']}",
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
                return make_html_response(self, 400, "<h1>Enlace inválido</h1><p>Falta el token de verificación.</p>")
            hashed_token = token_hash(token)
            with db() as conn:
                users = get_json_key(conn, "users", [])
                target = next((u for u in users if u.get("verifyTokenHash") == hashed_token), None)
                if not target:
                    return make_html_response(self, 404, "<h1>Enlace no encontrado</h1><p>Solicita un nuevo registro o contacta al administrador.</p>")
                if float(target.get("verifyExpiresAt") or 0) < time.time():
                    return make_html_response(self, 410, "<h1>Enlace expirado</h1><p>Regístrate nuevamente para recibir otro correo de verificación.</p>")
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
                "<p>Ya puedes iniciar sesión en Medic G. Si todavía no ves módulos, el administrador debe asignarte permisos.</p>"
                "<p><a href='/' style='color:#0d7a6b;font-weight:700;'>Ir al sistema</a></p>"
                "</body></html>",
            )
        if path == "/api/data":
            user = auth_user(self)
            if not user:
                return make_response(self, 401, {"error": "Sesión no válida"})
            if user.get("rol") == "paciente":
                return make_response(self, 403, {"error": "Usa el portal del paciente"})
            with db() as conn:
                rows = conn.execute("select key,value from app_data").fetchall()
            data = {row["key"]: json.loads(row["value"]) for row in rows}
            data["users"] = [public_user(u) for u in data.get("users", [])]
            return make_response(self, 200, {"user": public_user(user), "data": data})
        if path == "/api/patient/portal":
            user = auth_user(self)
            if not user:
                return make_response(self, 401, {"error": "Sesión no válida"})
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
            return make_response(self, 400, {"error": "JSON inválido"})
        except Exception:
            return make_response(self, 400, {"error": "JSON inválido"})

        if path == "/api/login":
            email = (payload.get("email") or "").strip().lower()
            password = payload.get("password") or ""
            with db() as conn:
                users = get_json_key(conn, "users", [])
            user = next((u for u in users if (u.get("email") or "").lower() == email), None)
            if not user or not verify_password(password, user.get("passHash") or user.get("pass")):
                return make_response(self, 401, {"error": "Correo o contraseña incorrectos"})
            if not user_email_verified(user) or user.get("estado") == "pendiente_verificacion":
                return make_response(self, 403, {"error": "Verifica tu correo electrónico antes de iniciar sesión"})
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

        if path == "/api/register":
            name = (payload.get("name") or "").strip()
            last = (payload.get("last") or "").strip()
            email = (payload.get("email") or "").strip().lower()
            password = payload.get("password") or ""
            if not name or not last or not email or len(password) < 6:
                return make_response(self, 400, {"error": "Completa nombre, apellido, correo y contraseña de mínimo 6 caracteres"})
            verify_token = secrets.token_urlsafe(32)
            verify_link = f"{app_base_url(self)}/api/verify-email?token={verify_token}"
            with db() as conn:
                users = get_json_key(conn, "users", [])
                if any((u.get("email") or "").lower() == email for u in users):
                    return make_response(self, 409, {"error": "Este correo ya está registrado"})
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
                "message": "Cuenta creada. Revisa tu correo para verificar tu cuenta antes de iniciar sesión.",
            }
            if not email_sent:
                response["message"] = "Cuenta creada, pero el servidor de correo no está configurado. Configura SMTP o Resend para enviar verificaciones."
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
                return make_response(self, 400, {"error": "Completa paciente, correo, teléfono, especialidad, fecha y hora"})
            with db() as conn:
                patient, patient_created = upsert_patient_from_payload(conn, {**payload, "origen": "Landing pública"})
                appointment = create_online_appointment(conn, patient, payload)
                audit(conn, None, "public_appointment", "citas", {"appointmentId": appointment["id"], "patientId": patient.get("id")})
            return make_response(self, 201, {
                "ok": True,
                "patientCreated": patient_created,
                "appointment": appointment,
                "message": "Cita solicitada correctamente. El centro médico la verá en agenda y te confirmará la atención.",
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
            return make_response(self, 401, {"error": "Sesión no válida"})

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
                return make_response(self, 403, {"error": "No tienes permiso para guardar este módulo"})
            with db() as conn:
                set_json_key(conn, key, value)
                audit(conn, user, "save", key)
            return make_response(self, 200, {"ok": True})

        if path == "/api/users":
            if user.get("rol") != "admin":
                return make_response(self, 403, {"error": "Solo el administrador puede crear usuarios"})
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
                return make_response(self, 400, {"error": "Completa nombre, apellido, correo y contraseña de mínimo 6 caracteres"})
            permissions = clean_permissions(payload.get("permissions"), rol)
            with db() as conn:
                users = get_json_key(conn, "users", [])
                if any((u.get("email") or "").lower() == email for u in users):
                    return make_response(self, 409, {"error": "Este correo ya está registrado"})
                patient_id = None
                if rol == "paciente":
                    patient, _ = upsert_patient_from_payload(conn, {
                        "name": name,
                        "last": last,
                        "email": email,
                        "origen": "Creado por administrador",
                    })
                    patient_id = patient.get("id")
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

