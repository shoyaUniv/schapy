#!/bin/sh

python manage.py migrate

python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='your_admin_username').exists():
    User.objects.create_superuser('your_admin_username', 'admin@example.com', 'your_password')
EOF

exec "$@"
