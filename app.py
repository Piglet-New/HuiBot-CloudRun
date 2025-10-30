import os
import logging
import sqlite3
import asyncio
import threading
from datetime import datetime
from flask import Flask, request, jsonify

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("huibot")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "").strip()
DB_PATH = os.environ.get("DB_PATH", "db/hui.db")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def db_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("""            CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT,
            slots INTEGER,
            face_value INTEGER,
            created_at TEXT
        );""")
    cur.execute("""            CREATE TABLE IF NOT EXISTS memberships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            user_id INTEGER,
            username TEXT,
            joined_at TEXT,
            UNIQUE(group_id, user_id)
        );""")
    conn.commit()
    conn.close()

init_db()

app_state = {
    "loop": None,
    "application": None,
    "started": False,
}

async def cmd_start(update, context):
    await update.message.reply_text(
        "👋 Chào bạn! Đây là Hụi Bot (Cloud Run + SQLite).\nGõ /menu để xem lệnh khả dụng."
    )

async def cmd_menu(update, context):
    await update.message.reply_text(
        "📋 Lệnh khả dụng:\n"
        "/start — chào hỏi\n"
        "/menu — menu lệnh\n"
        "/create_group <CODE> <NAME> <SLOTS> <FACE_VALUE>\n"
        "   Ví dụ: /create_group HUI001 HuiStrTuan 12 5000000\n"
        "/join <CODE> — tham gia dây hụi\n"
    )

async def cmd_create_group(update, context):
    try:
        args = context.args
        if len(args) < 4:
            await update.message.reply_text("❗Cú pháp: /create_group <CODE> <NAME> <SLOTS> <FACE_VALUE>")
            return
        code = args[0]
        name = args[1]
        slots = int(args[2])
        face_value = int(args[3])

        conn = db_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO groups(code, name, slots, face_value, created_at) VALUES(?,?,?,?,?)",
            (code, name, slots, face_value, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ Đã tạo dây {code} ({name}), {slots} suất, mệnh giá {face_value:,}đ.")
    except Exception as e:
        logger.exception("create_group error: %s", e)
        await update.message.reply_text("⚠️ Lỗi khi tạo dây. Kiểm tra cú pháp hoặc thử mã khác.")

async def cmd_join(update, context):
    try:
        args = context.args
        if len(args) < 1:
            await update.message.reply_text("❗Cú pháp: /join <CODE>")
            return
        code = args[0]

        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM groups WHERE code=?", (code,))
        row = cur.fetchone()
        if not row:
            await update.message.reply_text("❌ Không tìm thấy mã dây này.")
            conn.close()
            return
        group_id = row["id"]
        user = update.effective_user
        cur.execute(
            "INSERT OR IGNORE INTO memberships(group_id, user_id, username, joined_at) VALUES(?,?,?,?)",
            (group_id, user.id, user.username or "", datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ Tham gia dây {code} thành công.")
    except Exception as e:
        logger.exception("join error: %s", e)
        await update.message.reply_text("⚠️ Lỗi khi tham gia dây.")

async def echo_text(update, context):
    if update.message and update.message.text:
        await update.message.reply_text(f"✅ Bạn vừa gửi: {update.message.text}")

def build_app():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("menu", cmd_menu))
    application.add_handler(CommandHandler("create_group", cmd_create_group))
    application.add_handler(CommandHandler("join", cmd_join))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_text))
    return application

def run_bot_background():
    if app_state["started"]:
        return
    if not BOT_TOKEN:
        logger.warning("BOT_TOKEN is empty; bot will not start.")
        return

    loop = asyncio.new_event_loop()
    app_state["loop"] = loop

    async def _runner():
        app_state["application"] = build_app()
        await app_state["application"].initialize()
        await app_state["application"].start()
        logger.info("Telegram application started")
        while True:
            await asyncio.sleep(3600)

    def _thread():
        asyncio.set_event_loop(loop)
        loop.create_task(_runner())
        loop.run_forever()

    t = threading.Thread(target=_thread, name="tg-bot", daemon=True)
    t.start()
    app_state["started"] = True

run_bot_background()

@app.get("/")
def root():
    return "ok", 200

@app.get("/health")
def health():
    return jsonify(status="ok"), 200

@app.post("/webhook")
def webhook():
    expected = WEBHOOK_SECRET or ""
    got = request.args.get("secret", "")
    if expected and got != expected:
        return "forbidden", 403

    if not app_state.get("application") or not app_state.get("loop"):
        return "bot not started", 503

    data = request.get_json(silent=True) or {}
    try:
        update = Update.de_json(data, app_state["application"].bot)
        fut = asyncio.run_coroutine_threadsafe(
            app_state["application"].process_update(update),
            app_state["loop"]
        )
        fut.result(timeout=10)
    except Exception as e:
        logger.exception("webhook error: %s", e)
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
