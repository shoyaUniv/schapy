#!/bin/bash

# エラーが発生した場合にスクリプトを終了する
set -e

# データベースの準備を待機
echo "Waiting for database to be ready..."
until python ./src/manage.py showmigrations > /dev/null 2>&1; do
    echo "Database is unavailable - sleeping"
    sleep 3
done

# マイグレーションの実行
# echo "Running database migrations..."
# python ./src/manage.py migrate --noinput

python manage.py collectstatic --no-input
python manage.py migrate
python manage.py superuser

# daphneサーバーを起動
exec daphne -b 0.0.0.0 -p 8000 src.config.asgi:application
