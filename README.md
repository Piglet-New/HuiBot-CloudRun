# Hụi Bot – Cloud Run + SQLite (PTB v20)

Telegram bot đầy đủ chạy trên Cloud Run, lưu SQLite (db/hui.db).

## Bước 1 — Điền 2 biến trong `cloudrun.yaml`
```yaml
env:
  - name: WEBHOOK_SECRET
    value: "PUT-YOUR-SECRET-HERE"
  - name: BOT_TOKEN
    value: "PUT-YOUR-TELEGRAM-BOT-TOKEN-HERE"
```

## Bước 2 — GitHub Secrets (deploy)
- `GCP_PROJECT_ID` = <project-id>
- `GCP_REGION`     = <region>
- `GCP_SA_KEY`     = JSON key

## Bước 3 — Push → Actions deploy
- Lấy URL từ cuối log
- Test `/<health>` và `/`

## Bước 4 — Gắn webhook
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<RUN_URL>/webhook?secret=<YOUR_WEBHOOK_SECRET>
```

## Lệnh có sẵn
/start, /menu, /create_group, /join
