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
SESSIONS = {}


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


def get_json_key(conn, key, default=None):
    row = conn.execute("select value from app_data where key = ?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def set_json_key(conn, key, value):
    conn.execute(
        "insert into app_data(key,value,updated_at) values(?,?,?) "
        "on conflict(key) do update set value=excluded.value, updated_at=excluded.updated_at",
        (key, json.dumps(value, ensure_ascii=False), now_iso()),
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
        if not get_json_key(conn, "nextIds"):
            set_json_key(conn, "nextIds", {"pac": 6, "med": 5, "cita": 6, "fac": 1845, "esp": 7, "seg": 5, "user": 2})


def make_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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
            return make_response(self, 200, {"token": token, "user": public_user(user)})

        if path == "/api/logout":
            token = self.headers.get("Authorization", "").replace("Bearer ", "").strip()
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

