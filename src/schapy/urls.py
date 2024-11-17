from django.urls import path
from . import views

# アプリケーション名を指定
app_name = 'schapy'

urlpatterns = [
    path("", views.root, name="root"),
]