#!/bin/bash

# エラーが発生した場合にスクリプトを終了する
set -e

# データベースマイグレーション
python ./src/manage.py migrate

# スーパーユーザーを作成
python -c "\
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

# daphneサーバーを起動
exec daphne -b 0.0.0.0 -p 8000 src.config.asgi:application
