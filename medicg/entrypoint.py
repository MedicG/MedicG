"""Shared Vercel HTTP entrypoint; initialize once per worker without leaking errors."""
import logging
import threading
from medicg_app import MedicGHandler, init_db, make_response

class ProductionHandler(MedicGHandler):
    db_ready = False
    initialization_lock = threading.Lock()

    def ensure_database(self):
        if ProductionHandler.db_ready:
            return True
        with ProductionHandler.initialization_lock:
            if ProductionHandler.db_ready:
                return True
            try:
                init_db()
                ProductionHandler.db_ready = True
                return True
            except Exception as exc:
                logging.error("Database initialization failed (%s)", type(exc).__name__)
                return False

    def do_GET(self):
        if not self.ensure_database():
            return make_response(self, 503, {"error": "Servicio temporalmente no disponible. Intenta nuevamente."})
        return super().do_GET()

    def do_POST(self):
        if not self.ensure_database():
            return make_response(self, 503, {"error": "Servicio temporalmente no disponible. Intenta nuevamente."})
        return super().do_POST()
