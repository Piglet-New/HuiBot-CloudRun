import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from bot.bot_core import dp, bot, handle_update
from db import init_engine, run_migrations

load_dotenv()

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "dev")
PORT = int(os.environ.get("PORT", "8080"))

app = FastAPI(title="Hui Bot Cloud Run")

@app.on_event("startup")
async def on_startup():
    # Init DB engine and run light migrations
    await init_engine()
    await run_migrations()

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
