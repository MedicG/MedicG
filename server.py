from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from email.message import EmailMessage
import hashlib
import json
import os
import secrets
import smtplib
import sqlite3
import time

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("MEDICG_DB_PATH", BASE_DIR / "medicg.sqlite3"))
DATABASE_URL = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("POSTGRES_URL")
    or os.environ.get("POSTGRES_URL_NON_POOLING")
)
DB_DRIVER = "postgres" if DATABASE_URL else "sqlite"
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@medicg.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin123")
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
MAX_BODY_BYTES = int(os.environ.get("MAX_BODY_BYTES", str(12 * 1024 * 1024)))
PUBLIC_APP_URL = os.environ.get("PUBLIC_APP_URL", "").rstrip("/")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER or ADMIN_EMAIL)
SMTP_TLS = os.environ.get("SMTP_TLS", "true").lower() not in ("0", "false", "no")
SMTP_SSL = os.environ.get("SMTP_SSL", "false").lower() in ("1", "true", "yes")
SHOW_VERIFICATION_LINK = os.environ.get("SHOW_VERIFICATION_LINK", "false").lower() in ("1", "true", "yes")
SESSIONS = {}
ALLOWED_PERMISSIONS = {
    "dashboard", "agenda", "hce", "facturacion", "reportes", "pacientes",
    "medicos", "especialidades", "seguros", "quirofanos", "servicios",
    "examenes", "caja", "config",
}
ROLE_DEFAULT_PERMISSIONS = {
    "admin": sorted(ALLOWED_PERMISSIONS),
    "recepcion": ["agenda", "caja"],
    "secretaria": ["agenda", "caja"],
    "asistente": ["agenda", "caja"],
    "medico": ["hce"],
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
    if PUBLIC_APP_URL:
        return PUBLIC_APP_URL
    origin = handler.headers.get("Origin", "").rstrip("/")
    if origin:
        return origin
    proto = handler.headers.get("X-Forwarded-Proto", "").split(",")[0].strip().lower()
    proto = "https" if proto == "https" else "http"
    host = handler.headers.get("Host", f"{HOST}:{PORT}")
    return f"{proto}://{host}".rstrip("/")


def smtp_configured():
    return bool(SMTP_HOST and SMTP_FROM)


def send_verification_email(to_email, name, link):
    if not smtp_configured():
        return False, "SMTP no configurado"
    msg = EmailMessage()
    msg["Subject"] = "Verifica tu cuenta Medic G"
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(
        f"Hola {name},\n\n"
        "Gracias por registrarte en Medic G.\n\n"
        f"Verifica tu correo en este enlace:\n{link}\n\n"
        "Si no solicitaste esta cuenta, puedes ignorar este mensaje."
    )
    if SMTP_SSL:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            if SMTP_USER and SMTP_PASSWORD:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            if SMTP_TLS:
                smtp.starttls()
            if SMTP_USER and SMTP_PASSWORD:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
    return True, ""


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
        "createdAt": user.get("createdAt", ""),
        "estado": user.get("estado", "activo"),
        "emailVerified": user_email_verified(user),
    }


def clean_permissions(permissions, role):
    if role == "admin":
        return sorted(ALLOWED_PERMISSIONS)
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
        if path == "/health":
            return make_response(self, 200, {"ok": True})
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
            with db() as conn:
                rows = conn.execute("select key,value from app_data").fetchall()
            data = {row["key"]: json.loads(row["value"]) for row in rows}
            data["users"] = [public_user(u) for u in data.get("users", [])]
            return make_response(self, 200, {"user": public_user(user), "data": data})
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
                next_ids = get_json_key(conn, "nextIds", {})
                new_id = int(next_ids.get("user", len(users) + 1))
                next_ids["user"] = new_id + 1
                new_user = {
                    "id": new_id,
                    "name": name,
                    "last": last,
                    "email": email,
                    "passHash": hash_password(password),
                    "rol": "pendiente",
                    "permissions": [],
                    "estado": "pendiente_verificacion",
                    "emailVerified": False,
                    "verifyTokenHash": token_hash(verify_token),
                    "verifyExpiresAt": time.time() + 48 * 3600,
                    "createdAt": now_iso(),
                }
                users.append(new_user)
                set_json_key(conn, "users", users)
                set_json_key(conn, "nextIds", next_ids)
                audit(conn, None, "public_register", "users", {"createdUserId": new_id, "createdEmail": email})
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
                response["message"] = "Cuenta creada, pero el servidor de correo no está configurado. Configura SMTP para enviar verificaciones."
                response["emailError"] = email_error
            if SHOW_VERIFICATION_LINK:
                response["verificationLink"] = verify_link
            return make_response(self, 201, response)

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

