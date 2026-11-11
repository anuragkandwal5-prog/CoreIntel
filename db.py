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
                created_at TIMESTAMP NOT NULL DEFAULT now()
            )
        """)
        # purani table mein agar ye columns nahi hain to khud-ba-khud jod deta hai
        for coldef in [
            "email TEXT",
            "is_vip BOOLEAN NOT NULL DEFAULT FALSE",
            "is_admin BOOLEAN NOT NULL DEFAULT FALSE",
            "vip_requested BOOLEAN NOT NULL DEFAULT FALSE",
            "banned BOOLEAN NOT NULL DEFAULT FALSE",
            "balance NUMERIC NOT NULL DEFAULT 100000",
        ]:
            cur.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {coldef}")
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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS holdings (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                symbol TEXT NOT NULL,
                qty NUMERIC NOT NULL,
                avg_price NUMERIC NOT NULL,
                UNIQUE(username, symbol)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                qty NUMERIC NOT NULL,
                price NUMERIC NOT NULL,
                total NUMERIC NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT now()
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


def update_email(username, email):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET email=%s WHERE username=%s", (email, username))
        conn.commit()


def set_banned(username, value):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET banned=%s WHERE username=%s", (value, username))
        conn.commit()


def set_balance(username, amount):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET balance=%s WHERE username=%s", (amount, username))
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
        cur.execute("""
            SELECT username, email, is_vip, is_admin, vip_requested, banned, balance, created_at
            FROM users ORDER BY created_at
        """)
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


def get_holdings(username):
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT symbol, qty, avg_price FROM holdings WHERE username=%s AND qty>0 ORDER BY symbol", (username,))
        return cur.fetchall()


def get_trades(username, limit=20):
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT symbol, side, qty, price, total, created_at FROM trades WHERE username=%s ORDER BY id DESC LIMIT %s", (username, limit))
        return cur.fetchall()


def buy_asset(username, symbol, qty, price):
    """Returns (ok, message). Atomic: balance check + debit + holding update + trade log, one transaction."""
    total = qty * price
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT balance FROM users WHERE username=%s", (username,))
        bal = float(cur.fetchone()["balance"])
        if total > bal:
            return False, "Paisa kam hai is trade ke liye"
        cur.execute("SELECT qty, avg_price FROM holdings WHERE username=%s AND symbol=%s", (username, symbol))
        h = cur.fetchone()
        if h:
            old_qty = float(h["qty"]); old_avg = float(h["avg_price"])
            new_qty = old_qty + qty
            new_avg = (old_qty * old_avg + total) / new_qty
            cur.execute("UPDATE holdings SET qty=%s, avg_price=%s WHERE username=%s AND symbol=%s",
                        (new_qty, new_avg, username, symbol))
        else:
            cur.execute("INSERT INTO holdings (username, symbol, qty, avg_price) VALUES (%s,%s,%s,%s)",
                        (username, symbol, qty, price))
        cur.execute("UPDATE users SET balance=balance-%s WHERE username=%s", (total, username))
        cur.execute("INSERT INTO trades (username, symbol, side, qty, price, total) VALUES (%s,%s,%s,%s,%s,%s)",
                    (username, symbol, "buy", qty, price, total))
        conn.commit()
        return True, f"{qty} {symbol.upper()} khareeda"


def sell_asset(username, symbol, qty, price):
    """Returns (ok, message). Atomic: holding check + credit + holding update + trade log, one transaction."""
    total = qty * price
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT qty FROM holdings WHERE username=%s AND symbol=%s", (username, symbol))
        h = cur.fetchone()
        have = float(h["qty"]) if h else 0
        if qty > have:
            return False, "Itni quantity aapke paas nahi hai"
        new_qty = have - qty
        cur.execute("UPDATE holdings SET qty=%s WHERE username=%s AND symbol=%s", (new_qty, username, symbol))
        cur.execute("UPDATE users SET balance=balance+%s WHERE username=%s", (total, username))
        cur.execute("INSERT INTO trades (username, symbol, side, qty, price, total) VALUES (%s,%s,%s,%s,%s,%s)",
                    (username, symbol, "sell", qty, price, total))
        conn.commit()
        return True, f"{qty} {symbol.upper()} becha"
