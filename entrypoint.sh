#!/bin/bash

# エラーが発生した場合にスクリプトを終了する
set -e

# データベースの準備を待機する
echo "Waiting for database to be ready..."
until python ./src/manage.py showmigrations > /dev/null 2>&1; do
    echo "Database is unavailable - sleeping"
    sleep 3
done

# データベースマイグレーションの実行
echo "Running database migrations..."
if python ./src/manage.py migrate; then
    echo "Database migrations completed successfully"
else
    echo "Database migration failed"
    exit 1
fi

# スーパーユーザーを作成
echo "Creating superuser if it does not exist..."
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
