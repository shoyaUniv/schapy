from django.urls import re_path
from . import consumers

# WebSocket接続のルーティングパターンを定義しています。
# クライアントから "ws/chat/ルーム名/" という形式で WebSocket 接続が来た場合、
# その接続を ChatConsumer のインスタンスに渡すように設定されています。
# (?P<room_name>\w+) という部分は、URL内で動的に変化する「ルーム名」をキャプチャしています。
# re_path() を使用して正規表現ベースでURLを定義しています。

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_name>\w+)/$", consumers.ChatConsumer.as_asgi()),
]