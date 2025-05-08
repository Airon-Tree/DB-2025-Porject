import psycopg2, psycopg2.pool
from psycopg2.extras import RealDictCursor
from flask import g
from config import DB_SETTINGS

_pool: psycopg2.pool.SimpleConnectionPool | None = None


def init_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            cursor_factory=RealDictCursor,
            **DB_SETTINGS,
        )


def get_conn():
    if "db_conn" not in g:
        g.db_conn = _pool.getconn()
    return g.db_conn


def release_conn(_exc):
    conn = g.pop("db_conn", None)
    if conn is not None:
        _pool.putconn(conn, close=False)


def run(sql, params=None, fetchone=False, commit=False):
    """Thin wrapper around cursor execute."""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        if commit:
            conn.commit()
        if cur.description:  # SELECT / RETURNING
            return cur.fetchone() if fetchone else cur.fetchall()
        
        