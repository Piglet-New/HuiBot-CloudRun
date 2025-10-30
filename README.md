# Hụi Bot – Cloud Run Starter (No-Dev Copy-Paste)

Đây là gói sẵn sàng deploy trên **Google Cloud Run**. Bạn chỉ cần copy-paste vào repo GitHub, đặt vài Secrets, push là chạy.

## 0) Bạn cần chuẩn bị
- Token bot Telegram (tạo bot qua @BotFather).
- 1 Project GCP (ví dụ `huibot-368349924534`) và đã bật Cloud Run.
- 1 Service Account có quyền deploy (Cloud Run Admin, Service Account User, Artifact Registry Reader).
- Firestore có thể bật sau (để lưu dữ liệu bền), **không bắt buộc** cho bản echo demo.

## 1) Đặt GitHub Secrets
Vào **Settings → Secrets and variables → Actions → New repository secret** và tạo:
- `GCP_PROJECT_ID` : ID project GCP (ví dụ `huibot-368349924534`)
- `GCP_REGION` : vùng deploy (ví dụ `asia-southeast1`)
- `GCP_SA_KEY` : JSON key của service account (copy nội dung file .json vào đây)
- `WEBHOOK_SECRET` : chuỗi bí mật tuỳ bạn (ví dụ `abc123`)
- `BOT_TOKEN` : token Telegram bot (ví dụ `123456:ABC-...`)

## 2) Copy-paste toàn bộ folder này vào repo GitHub của bạn
Cấu trúc chính:
```
app.py
requirements.txt
Dockerfile
cloudrun.yaml
.github/workflows/deploy.yml
```

## 3) Push code lên nhánh `main`
- GitHub Actions sẽ tự build image và deploy Cloud Run.
- Cuối job sẽ in ra **URL** của service. Ví dụ: `https://huibot-xxxxxx-asia-southeast1.run.app`

## 4) Test health
Mở trình duyệt hoặc dùng curl:
- `https://<RUN_URL>/health` → phải trả `{ "status": "ok" }` với mã 200
- `https://<RUN_URL>/` → trả "ok"

Nếu lỗi 404, kiểm tra lại `cloudrun.yaml` và đảm bảo image đã push thành công.

## 5) Gắn Webhook Telegram
Mở trình duyệt (đổi token, URL, secret cho đúng):
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<RUN_URL>/webhook?secret=<WEBHOOK_SECRET>

Trả về `true` là thành công. Giờ hãy nhắn tin cho bot trong Telegram — bot sẽ **echo** lại tin nhắn của bạn.

## 6) Nâng cấp lưu dữ liệu bền (tuỳ chọn)
- Bật Firestore (Native mode) trong GCP Console.
- Gán vai trò `Datastore User` hoặc `Firestore User` cho service account của Cloud Run.
- Dùng file `sqlite_to_firestore.py` để migrate nếu bạn có SQLite cũ.

## Ghi chú
- Để luôn "wakeup liền": đã bật `minInstances: 1` trong `cloudrun.yaml`.
- Tuỳ mức dùng mà vẫn trong Free Tier. Nếu vượt, GCP sẽ tính phí.
