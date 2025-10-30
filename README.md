# HuiBot – Cloud Run (Preset Project/Region)

Đã cài sẵn:
- Project ID: huibot-368349924534
- Region: asia-southeast1
- Service: huibot
- minInstances=1 (wake up liền)

## Bước 1 — Điền 2 bí mật trong file `cloudrun.yaml`
```yaml
env:
  - name: WEBHOOK_SECRET
    value: "PUT-YOUR-SECRET-HERE"
  - name: BOT_TOKEN
    value: "PUT-YOUR-TELEGRAM-BOT-TOKEN-HERE"
```

## Bước 2 — Thêm GitHub Secrets (để deploy được)
- `GCP_PROJECT_ID` = huibot-368349924534
- `GCP_REGION` = asia-southeast1
- `GCP_SA_KEY` = nội dung JSON key của service account

## Bước 3 — Push lên `main` → Actions deploy
- Lấy URL Cloud Run từ cuối log.
- Kiểm tra: `/<health>` và `/` trả 200.

## Bước 4 — Set Webhook Telegram
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<RUN_URL>/webhook?secret=<YOUR_WEBHOOK_SECRET>
```
