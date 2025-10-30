import os
import logging
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("huibot")

TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

@app.get("/")
def root():
    return "ok", 200

@app.get("/health")
def health():
    return jsonify(status="ok"), 200

def send_message(chat_id: int, text: str):
    if not TELEGRAM_TOKEN:
        logger.error("BOT_TOKEN is not set")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": chat_id, "text": text})
        if resp.status_code != 200:
            logger.error("sendMessage failed: %s %s", resp.status_code, resp.text)
    except Exception as e:
        logger.exception("sendMessage exception: %s", e)

@app.post("/webhook")
def telegram_webhook():
    expected = WEBHOOK_SECRET or ""
    got = request.args.get("secret", "")
    if expected and got != expected:
        return "forbidden", 403

    update = request.get_json(silent=True) or {}
    logger.info("Update: %s", update)

    try:
        message = update.get("message") or update.get("edited_message") or {}
        if message:
            chat = message.get("chat") or {}
            chat_id = chat.get("id")
            text = message.get("text") or ""
            if chat_id and text:
                reply = f"✅ Hụi Bot Cloud Run đã hoạt động! Bạn vừa gửi: {text}"
                send_message(chat_id, reply)
    except Exception as e:
        logger.exception("handle update failed: %s", e)

    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
