FROM python:3.12-slim

WORKDIR /app

# Cài đặt thư viện hệ thống cần thiết cho psycopg2 và vnstock
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Lệnh chạy Backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]