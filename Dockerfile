FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --upgrade pip setuptools wheel

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080

# ✅ Chạy bằng uvicorn và reload webhook startup logs rõ ràng
CMD exec uvicorn app:app --host 0.0.0.0 --port $PORT
