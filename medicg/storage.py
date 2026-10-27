"""Bounded connection pools and explicit read/write transaction boundaries.

Lock scopes for write transactions (``lock`` argument):
  * ``"global"`` (default): serializes writes that read-modify-write the JSON
    aggregates stored in ``app_data``. Keeps the original safety guarantees.
  * ``None``: no application lock. Use only for writes to independent tables
    (sessions, audit_log, login throttling) that never rewrite app_data.
  * any other string: a named lock (for example ``"telehealth:42"``) so unrelated
    operations no longer queue behind each other.

Within one transaction the raw JSON text of each app_data key is cached, so
repeated ``get_json_key`` calls avoid extra round trips to the database.
"""
import atexit
import hashlib
import os
import sqlite3
import threading

_pools = {}
_pool_lock = threading.Lock()
GLOBAL_LOCK_ID = 734219608


def lock_id(name):
    if name == "global":
        return GLOBAL_LOCK_ID
    digest = hashlib.sha256(str(name).encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], "big", signed=True)
    return value if value != GLOBAL_LOCK_ID else value + 1


class DatabaseConnection:
    def __init__(self, connection, driver, release=None, read_only=False, lock="global"):
        self.connection = connection
        self.driver = driver
        self.release = release
        self.read_only = read_only
        self.lock = lock
        self.json_cache = {}

    def execute(self, sql, params=()):
        if self.driver == 'postgres':
            sql = sql.replace('?', '%s')
        return self.connection.execute(sql, params or ())

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.json_cache = {}
        if self.release:
            self.release(self.connection)
        else:
            self.connection.close()

    def __enter__(self):
        try:
            if self.driver == 'postgres':
                if self.read_only:
                    self.execute('SET TRANSACTION READ ONLY')
                elif self.lock:
                    self.execute('select pg_advisory_xact_lock(?)', (lock_id(self.lock),))
            elif self.read_only:
                self.execute('PRAGMA query_only = ON')
                self.execute('BEGIN')
            elif self.lock:
                self.execute('BEGIN IMMEDIATE')
            else:
                self.execute('BEGIN')
            return self
        except Exception:
            self.rollback()
            self.close()
            raise

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type:
                self.rollback()
            else:
                self.commit()
        finally:
            self.close()
        return False


def _sqlite_connect(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA busy_timeout=15000')
    except sqlite3.DatabaseError:
        pass
    return conn


def connect(driver, url, path, read_only=False, lock="global"):
    if driver == 'postgres':
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool
        with _pool_lock:
            pool = _pools.get(url)
            if pool is None:
                pool = ConnectionPool(
                    conninfo=url, min_size=0,
                    max_size=max(1, min(16, int(os.environ.get('DB_POOL_MAX_SIZE', '4')))),
                    timeout=10, max_waiting=32, max_idle=60, max_lifetime=300,
                    kwargs={'row_factory':dict_row,'connect_timeout':10,'prepare_threshold':None},
                    check=ConnectionPool.check_connection, open=True,
                )
                _pools[url] = pool
                atexit.register(pool.close)
        return DatabaseConnection(pool.getconn(), driver, release=pool.putconn, read_only=read_only, lock=lock)
    if os.environ.get('VERCEL') and os.environ.get('ALLOW_SQLITE_ON_VERCEL','').lower() not in ('1','true','yes'):
        raise RuntimeError('PostgreSQL no está configurado')
    return DatabaseConnection(_sqlite_connect(path), 'sqlite', read_only=read_only, lock=lock)
