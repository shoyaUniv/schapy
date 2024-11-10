# エラーが発生した場合にスクリプトを終了する
# set -e

# # データベースの準備を待機
# echo "Waiting for database to be ready..."
# until python ./src/manage.py showmigrations > /dev/null 2>&1; do
#     echo "Database is unavailable - sleeping"
#     sleep 3
# done

# # 静的ファイルを収集し、マイグレーションを実行
# python ./src/manage.py collectstatic --no-input
# python ./src/manage.py migrate

# # スーパーユーザーの作成
# python ./src/manage.py superuser

# # Daphneサーバーを起動
# exec daphne -b 0.0.0.0 -p 8000 src.config.asgi:application

#!/bin/bash

# エラーが発生した場合にスクリプトを終了する
set -e

# データベースの準備を待機
echo "Waiting for database to be ready..."
until python ./src/manage.py showmigrations > /dev/null 2>&1; do
    echo "Database is unavailable - sleeping"
    sleep 3
done

# 静的ファイルの収集
python ./src/manage.py collectstatic --no-input

# マイグレーションを確実に実行
echo "Running database migrations..."
python ./src/manage.py migrate --noinput

# スーパーユーザーの作成
python ./src/manage.py superuser

# Daphneサーバーを起動
exec daphne -b 0.0.0.0 -p 8000 src.config.asgi:application


