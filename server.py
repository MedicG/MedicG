from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import hashlib
import json
import os
import secrets
import sqlite3
import time

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("MEDICG_DB_PATH", BASE_DIR / "medicg.sqlite3"))
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@medicg.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin123")
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
SESSIONS = {}
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


def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
        "createdAt": user.get("createdAt", ""),
        "estado": user.get("estado", "activo"),
    }


def init_db():
    with db() as conn:
        conn.execute(
            "create table if not exists app_data("
            "key text primary key, value text not null, updated_at text not null)"
        )
        conn.execute(
            "create table if not exists audit_log("
            "id integer primary key autoincrement, ts text not null, user_id integer, "
            "email text, action text not null, data_key text, detail text)"
        )
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
                    "estado": "activo",
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
            set_json_key(conn, "nextIds", {"pac": 6, "med": 5, "cita": 6, "fac": 1845, "esp": 7, "seg": 5, "user": 2, "qx": 3, "eq": 3, "st": 3, "caja": 1})
        else:
            changed_ids = False
            for key, value in {"qx": 3, "eq": 3, "st": 3, "caja": 1}.items():
                if key not in next_ids:
                    next_ids[key] = value
                    changed_ids = True
            if changed_ids:
                set_json_key(conn, "nextIds", next_ids)


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


def read_body(handler):
    length = int(handler.headers.get("Content-Length", "0") or "0")
    return json.loads(handler.rfile.read(length).decode("utf-8") or "{}")


def auth_user(handler):
    token = handler.headers.get("Authorization", "").replace("Bearer ", "").strip()
    session = SESSIONS.get(token)
    if not session or session["exp"] < time.time():
        return None
    return session["user"]


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
        except Exception:
            return make_response(self, 400, {"error": "JSON inválido"})

        if path == "/api/login":
            email = (payload.get("email") or "").strip().lower()
            password = payload.get("password") or ""
            with db() as conn:
                users = get_json_key(conn, "users", [])
            user = next((u for u in users if (u.get("email") or "").lower() == email), None)
            if not user or user.get("estado", "activo") != "activo" or not verify_password(password, user.get("passHash") or user.get("pass")):
                return make_response(self, 401, {"error": "Correo o contraseña incorrectos"})
            token = secrets.token_urlsafe(32)
            SESSIONS[token] = {"user": user, "exp": time.time() + 24 * 3600}
            with db() as conn:
                audit(conn, user, "login", "session")
            return make_response(self, 200, {"token": token, "user": public_user(user)})

        if path == "/api/logout":
            token = self.headers.get("Authorization", "").replace("Bearer ", "").strip()
            session = SESSIONS.get(token)
            if session:
                with db() as conn:
                    audit(conn, session["user"], "logout", "session")
            SESSIONS.pop(token, None)
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
            with db() as conn:
                set_json_key(conn, key, value)
                audit(conn, user, "save", key)
            return make_response(self, 200, {"ok": True})

        if path == "/api/users":
            if user.get("rol") != "admin":
                return make_response(self, 403, {"error": "Solo el administrador puede crear usuarios"})
            name = (payload.get("name") or "").strip()
            last = (payload.get("last") or "").strip()
            email = (payload.get("email") or "").strip().lower()
            password = payload.get("password") or ""
            rol = payload.get("rol") or "recepcion"
            if not name or not last or not email or len(password) < 6:
                return make_response(self, 400, {"error": "Completa nombre, apellido, correo y contraseña de mínimo 6 caracteres"})
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
                    "estado": "activo",
                    "createdAt": now_iso(),
                }
                users.append(new_user)
                set_json_key(conn, "users", users)
                set_json_key(conn, "nextIds", next_ids)
                audit(conn, user, "create_user", "users", {"createdUserId": new_id, "createdEmail": email, "rol": rol})
            return make_response(self, 200, {"user": public_user(new_user)})

        return make_response(self, 404, {"error": "Ruta no encontrada"})

    def do_OPTIONS(self):
        return make_response(self, 200, {"ok": True})


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), MedicGHandler)
    print("Medic G con base de datos SQLite")
    print(f"Abre: http://{HOST}:{PORT}")
    print(f"Base de datos: {DB_PATH}")
    server.serve_forever()

