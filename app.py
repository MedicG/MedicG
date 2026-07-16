from http.server import BaseHTTPRequestHandler

from medicg_app import MedicGHandler, init_db, make_response


class handler(MedicGHandler, BaseHTTPRequestHandler):
    db_ready = False
    db_error = None

    def ensure_database(self):
        if handler.db_ready:
            return True
        try:
            init_db()
            handler.db_ready = True
            handler.db_error = None
            return True
        except Exception as exc:
            handler.db_error = exc
            return False

    def database_error(self):
        detail = str(handler.db_error or "No se pudo inicializar la base de datos")
        return make_response(self, 500, {"error": detail})

    def do_GET(self):
        if not self.ensure_database():
            return self.database_error()
        return super().do_GET()

    def do_POST(self):
        if not self.ensure_database():
            return self.database_error()
        return super().do_POST()

    def do_OPTIONS(self):
        return super().do_OPTIONS()
