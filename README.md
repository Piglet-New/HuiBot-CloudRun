# Hụi Bot – Cloud Run (SQLite, webhook-first)

Port từ bản Vercel/Postgres sang Cloud Run + SQLite, giữ nguyên lệnh chính.

## Secrets cần có (Repo → Settings → Secrets → Actions)
- `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_SA_KEY`
- `BOT_TOKEN`, `WEBHOOK_SECRET`
- (tuỳ chọn) `ADMIN_CHAT_ID`

## Triển khai
1) Tải toàn bộ thư mục này lên repo → branch `main`.
2) Action sẽ build & deploy. Cuối log có **Service URL**.
3) Test `https://<RUN_URL>/health` → `{"status":"ok"}`
4) Bot tự setWebhook theo URL mới (dùng `?secret=...`).

## Lệnh
/tao, /tham, /hen, /danhsach, /tomtat, /hottot, /dong, /baocao, /lenh
