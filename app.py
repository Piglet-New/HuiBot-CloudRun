# app.py
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "dev")
PORT = int(os.environ.get("PORT", "8080"))
MIGRATE_ON_START = os.getenv("MIGRATE_ON_START", "false").lower() == "true"

app = FastAPI(title="Hui Bot Cloud Run")

@app.on_event("startup")
async def on_startup():
    # KHÔNG import hay chạm DB ở import-time để container boot nhanh
    if MIGRATE_ON_START:
        try:
            from db import init_engine, run_migrations  # lazy import
            await init_engine()
            await run_migrations()
            print("DB init & migrations completed")
        except Exception as e:
            # Không để crash container khi migrate lỗi
            print("Startup DB init error:", e)

@app.get("/healthz", response_class=PlainTextResponse)
async def healthz():
    return "ok"

@app.post(f"/webhook/{{secret}}")
async def telegram_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="forbidden")

    # Import bot khi cần dùng, tránh crash ở boot
    try:
        from bot.bot_core import handle_update  # lazy import
    except Exception as e:
        # log để xem lỗi trong Cloud Run logs
        print("Import bot_core error:", e)
        raise HTTPException(status_code=500, detail="bot init failed")

    data = await request.json()
    await handle_update(data)
    return {"ok": True}
