"""
Database layer — Postgres (Neon) ke liye.
Render par DATABASE_URL environment variable set hona chahiye.
"""
import os
import psycopg2
import psycopg2.extras


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def init_db():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                is_vip BOOLEAN NOT NULL DEFAULT FALSE,
                is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                vip_requested BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT now()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                username TEXT,
                text TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT now()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()


def get_user(username):
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        return cur.fetchone()


def create_user(username, password_hash, email):
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT COUNT(*) AS n FROM users")
        is_first = cur.fetchone()["n"] == 0        # sabse pehla user apne aap admin+VIP
        cur.execute(
            "INSERT INTO users (username, password_hash, email, is_admin, is_vip) "
            "VALUES (%s,%s,%s,%s,%s) RETURNING *",
            (username, password_hash, email, is_first, is_first),
        )
        row = cur.fetchone()
        conn.commit()
        return row


def set_password(username, password_hash):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET password_hash=%s WHERE username=%s", (password_hash, username))
        conn.commit()


def rename_user(old, new):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET username=%s WHERE username=%s", (new, old))
        conn.commit()


def request_vip(username):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET vip_requested=TRUE WHERE username=%s", (username,))
        conn.commit()


def set_vip(username, value):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET is_vip=%s, vip_requested=FALSE WHERE username=%s", (value, username))
        conn.commit()


def list_users():
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT username, email, is_vip, is_admin, vip_requested, created_at "
            "FROM users ORDER BY created_at"
        )
        return cur.fetchall()


def log_event(username, text):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO logs (username, text) VALUES (%s,%s)", (username, text))
        conn.commit()


def recent_logs(limit=30):
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT username, text, created_at FROM logs ORDER BY id DESC LIMIT %s", (limit,))
        return cur.fetchall()


def get_setting(key, default=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT value FROM settings WHERE key=%s", (key,))
        row = cur.fetchone()
        return row[0] if row else default


def set_setting(key, value):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO settings (key, value) VALUES (%s,%s) "
            "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value",
            (key, value),
        )
        conn.commit()
