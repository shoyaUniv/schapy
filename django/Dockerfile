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

# プロジェクト全体をコピー
COPY . /code/

# データベースマイグレーション（絶対パスで指定）
RUN python /code/src/manage.py migrate

# スーパーユーザーを作成
RUN python -c "\
import os; \
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings'); \
import django; \
django.setup(); \
from django.contrib.auth import get_user_model; \
from django.db.utils import IntegrityError; \
User = get_user_model(); \
if not User.objects.filter(username='admin').exists(): \
    try: \
        User.objects.create_superuser('admin', 'admin@example.com', 'admin'); \
        print('Superuser created successfully'); \
    except IntegrityError: \
        print('Superuser already exists'); \
"

# アプリケーションの起動コマンド（src ディレクトリで ASGI アプリケーションを指定）
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "src.config.asgi:application"]

