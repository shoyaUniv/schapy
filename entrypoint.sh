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

# スーパーユーザーの作成（エラー回避のためスクリプト化を推奨）
echo "from django.contrib.auth import get_user_model; \
User = get_user_model(); \
User.objects.filter(username='admin').exists() or \
User.objects.create_superuser('admin', 'admin@example.com', 'adminpassword')" | python ./src/manage.py shell

# Daphneサーバーを起動
exec daphne -b 0.0.0.0 -p 8000 src.config.asgi:application
