import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from bot.bot_core import dp, bot, handle_update
from db import init_engine, run_migrations

load_dotenv()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "dev")
PORT = int(os.getenv("PORT", "8080"))

app = FastAPI(title="Hui Bot Cloud Run")

# 🚀 Khởi tạo database và migrate khi container start
@app.on_event("startup")
async def on_startup():
    await init_engine()
    await run_migrations()
    print("✅ DB initialized & migrations done!")


# ✅ Health check cho Cloud Run
@app.get("/healthz", response_class=PlainTextResponse)
async def healthz():
    return "ok"


# ✅ Telegram Webhook endpoint
@app.post("/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="forbidden")

    data = await request.json()
    await handle_update(data)
    return {"ok": True}


# 🏃 Run local mode (không dùng khi deploy)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
