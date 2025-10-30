import os, sqlite3, json

DB_PATH = os.environ.get("DB_PATH", "db/hui.db")

def db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute("""    CREATE TABLE IF NOT EXISTS lines(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        period_days INTEGER,
        start_date TEXT,
        legs INTEGER,
        contrib INTEGER,
        bid_type TEXT,
        bid_value INTEGER,
        status TEXT,
        base_rate REAL,
        cap_rate REAL,
        thau_rate REAL,
        remind_hour INTEGER DEFAULT 8,
        remind_min  INTEGER DEFAULT 0,
        last_remind_iso TEXT
    );""")
    cur.execute("""    CREATE TABLE IF NOT EXISTS rounds(
        line_id INTEGER,
        k INTEGER,
        bid INTEGER,
        round_date TEXT,
        PRIMARY KEY(line_id, k)
    );""")
    cur.execute("""    CREATE TABLE IF NOT EXISTS payments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        line_id INTEGER,
        pay_date TEXT,
        amount INTEGER
    );""")
    cur.execute("""    CREATE TABLE IF NOT EXISTS config(
        key TEXT PRIMARY KEY,
        value TEXT
    );""")
    conn.commit()
    conn.close()

def ensure_schema():
    return True

def cfg_get(key, default=None):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key=?", (key,))
    row = cur.fetchone()
    conn.close()
    if not row: return default
    try:
        import json
        return json.loads(row["value"])
    except Exception:
        return default

def cfg_set(key, value):
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO config(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(value)))
    conn.commit(); conn.close()

def get_all(q, params=()):
    conn = db(); cur = conn.cursor()
    cur.execute(q, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def exec_sql(q, params=()):
    conn = db(); cur = conn.cursor()
    cur.execute(q, params)
    conn.commit(); conn.close()

def insert_and_get_id(q, params=()):
    conn = db(); cur = conn.cursor()
    cur.execute(q, params)
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id
