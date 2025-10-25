# app.py
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
from bot.bot_core import dp, bot, handle_update
from db import init_engine, run_migrations

load_dotenv()

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "dev")
PORT = int(os.environ.get("PORT", "8080"))
MIGRATE_ON_START = os.getenv("MIGRATE_ON_START", "false").lower() == "true"  # <— thêm dòng này

app = FastAPI(title="Hui Bot Cloud Run")

@app.on_event("startup")
async def on_startup():
    # Chỉ chạy DB init/migration khi thật sự cần
    if MIGRATE_ON_START:
        try:
            await init_engine()
            await run_migrations()
            print("DB init & migrations completed")
        except Exception as e:
            # Đừng làm container crash khi deploy
            print("Startup DB init error:", e)

@app.get("/healthz", response_class=PlainTextResponse)
async def healthz():
    return "ok"

@app.post(f"/webhook/{{secret}}")
async def telegram_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="forbidden")
    data = await request.json()
    await handle_update(data)
    return {"ok": True}
