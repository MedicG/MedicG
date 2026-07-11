from http.server import ThreadingHTTPServer
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
API_DIR = ROOT / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from medicg_app import DB_DRIVER, DB_PATH, HOST, PORT, MedicGHandler, init_db


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), MedicGHandler)
    print(f"Medic G con base de datos {DB_DRIVER}")
    print(f"Abre: http://{HOST}:{PORT}")
    print(f"Base de datos: {DB_PATH if DB_DRIVER == 'sqlite' else 'PostgreSQL'}")
    server.serve_forever()
