# Hụi Bot (Cloud Run, Postgres, Webhook) — Wizard UI

This package ports the **SQLite Wizard version** to a **Cloud Run** deploy, using:
- **aiogram 3.x** (Telegram bot)
- **FastAPI** (webhook endpoint)
- **SQLAlchemy 2.x** + **asyncpg** (PostgreSQL)
- **Alembic-free simple migration** via `python -m migrate`

## Features
- Inline keyboard **Menu**: Tạo dây, Nhập thâm, Đặt giờ nhắc, Danh sách, Tóm tắt, Gợi ý hốt
- Text commands: `/tao`, `/tham`, `/hen`, `/danhsach`, `/tomtat`, `/hottot`, `/dong`, `/baocao`
- Wizard flows mirror the original SQLite UX, but data persists in Postgres
- Secure webhook with secret path

---

## 1) Configuration

Copy `.env.example` to `.env` and fill:

```
BOT_TOKEN=123456:ABC...            # Telegram Bot token
ADMIN_CHAT_ID=123456789            # Your Telegram user/chat id (optional)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
WEBHOOK_BASE=https://<cloud-run-domain>   # e.g. https://huibot-xxxxx-uc.a.run.app
WEBHOOK_SECRET=any-string-secret          # used for path hardening
PORT=8080                                 # Cloud Run default
```

> For Neon: `postgresql+asyncpg://neondb_owner:password@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`

---

## 2) Local run (optional)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 1) Run migration
python -m migrate

# 2) Start server (FastAPI + aiogram webhook)
uvicorn app:app --host 0.0.0.0 --port 8080 --reload
```

Set webhook once (in another shell):

```bash
python -m tools.set_webhook
```

---

## 3) Docker (Cloud Run)

```bash
# Build
docker build -t gcr.io/PROJECT_ID/huibot:latest .

# Push
docker push gcr.io/PROJECT_ID/huibot:latest

# Deploy to Cloud Run
gcloud run deploy huibot   --image gcr.io/PROJECT_ID/huibot:latest   --region asia-southeast1   --platform managed   --allow-unauthenticated   --set-env-vars BOT_TOKEN=xxx,ADMIN_CHAT_ID=123,WEBHOOK_BASE=https://huibot-xxxx-uc.a.run.app,WEBHOOK_SECRET=secret,DATABASE_URL=postgresql+asyncpg://...   --port 8080
```

After deploy, visit:
- `GET /healthz` → `ok`
- `POST /webhook/<WEBHOOK_SECRET>` → Telegram webhook target (Cloud Run receives from Telegram)

To update webhook to the Cloud Run domain:
```bash
python -m tools.set_webhook
```

---

## 4) Data Model (simplified)

- **pots** (dây hụi)
  - id, name, cycle ('tuan'|'thang'), start_date, slots, face_value, floor_pct, cap_pct, fee_pct, is_closed
- **members**
  - id, chat_id, name (optional)
- **bids** (thâm / đấu thầu)
  - id, pot_id, member_id, amount, bid_date
- **reminders**
  - id, pot_id, chat_id, hh:mm string

---

## 5) Notes
- This is a clean port focused on stability; business rules are basic but the **Wizard UX** is preserved.
- Extend handlers in `bot/handlers_*.py`.




// preparing for PR
