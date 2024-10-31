#!/bin/bash

set -e  # エラー発生時にスクリプトを終了する

# 環境変数の確認
if [ -z "$ADMIN_USERNAME" ] || [ -z "$ADMIN_EMAIL" ] || [ -z "$ADMIN_PASSWORD" ]; then
    echo "エラー: 環境変数 ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_PASSWORD が設定されていません。"
    exit 1
fi

# データベースマイグレーション
python manage.py migrate

# スーパーユーザーの作成
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username="${ADMIN_USERNAME}").exists():
    User.objects.create_superuser("${ADMIN_USERNAME}", "${ADMIN_EMAIL}", "${ADMIN_PASSWORD}")
EOF

# コマンドを実行
exec "$@"
