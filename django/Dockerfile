# FROM python:3.11-slim

# ENV PYTHONUNBUFFERED 1

# WORKDIR /code

# COPY . /code/

# RUN pip install -r requirements.txt

# RUN python /code/src/superuser.py

# ---------------------------------------------------------------

# FROM python:3.11-slim

# ENV PYTHONUNBUFFERED 1

# WORKDIR /code

# COPY . /code/
# RUN pip install -r requirements.txt

# COPY entrypoint.sh /code/entrypoint.sh
# RUN chmod +x /code/entrypoint.sh

# ENTRYPOINT ["/code/entrypoint.sh"]

# CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
# ---------------------------------------------------------------

FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1

# 作業ディレクトリの設定
WORKDIR /code

# requirements.txt をコピーして依存関係をインストール
COPY requirements.txt /code/
RUN pip install -r requirements.txt

# プロジェクト全体とエントリポイントスクリプトをコピー
COPY . /code/
COPY entrypoint.sh /code/entrypoint.sh

# スクリプトに実行権限を付与
RUN chmod +x /code/entrypoint.sh

# エントリポイントスクリプトを実行
ENTRYPOINT ["/code/entrypoint.sh"]

