# Python 3.10 ベースイメージを使用
FROM python:3.10-slim

# OSパッケージをインストール（OpenCV依存ライブラリ）
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリを作成
WORKDIR /app

# 必要なライブラリのインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY app.py .

# Gunicornを使ってFlaskアプリケーションを実行
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app", "--timeout", "120", "--workers", "3"]
