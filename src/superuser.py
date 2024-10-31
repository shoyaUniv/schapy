from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError

User = get_user_model()

# スーパーユーザーが既に存在しない場合にのみ作成する
if not User.objects.filter(username='admin').exists():
    try:
        User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin'
        )
        print("Superuser created successfully")
    except IntegrityError:
        print("Superuser already exists")
