FROM python:3.11-slim 

ENV PYTHONUNBUFFERED 1 

WORKDIR /code 

# Tesseract の依存関係をインストール
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /code/ 

# pytesseract を requirements.txt に追加する必要がある場合
RUN pip install -r requirements.txt 

COPY . /code/
