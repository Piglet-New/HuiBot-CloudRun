FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt ./

# Upgrade installer tooling to avoid resolver issues
RUN python -m pip install --upgrade pip setuptools wheel

# Install deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Run your app
CMD ["python", "app.py"]
