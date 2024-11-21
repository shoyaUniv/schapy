from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("<str:room_name>/", views.room, name="room"),
    path('api/send_line_message/', views.send_line_message, name='send_line_message'),
]