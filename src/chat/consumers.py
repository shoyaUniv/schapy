import json

from django.urls import reverse
from django.conf import settings

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer

from langchain.agents import Tool, initialize_agent, AgentType
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_community.chat_models import ChatOpenAI

OPENAI_API_KEY = settings.OPENAI_API_KEY
OPENAI_API_BASE = settings.OPENAI_API_URL

class ChatConsumer(WebsocketConsumer):
    # WebSocket接続時に呼ばれるメソッド
    def connect(self):
        # URLからルーム名を取得
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        # ルームグループ名を設定
        self.room_group_name = "chat_%s" % self.room_name
        # ルームグループに参加
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name, self.channel_name
        )
        # WebSocket接続を受け入れる
        self.accept()

    # WebSocket切断時に呼ばれるメソッド
    def disconnect(self, close_code):
        # ルームグループから退出
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name, self.channel_name
        )

    # WebSocketからメッセージを受信した時に呼ばれるメソッド
    def receive(self, text_data):
        # 受信したメッセージをJSON形式にデコード
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        
        # ChatGPT APIを使用して、メッセージをポジティブな絵文字に変換
        chat = ChatOpenAI(
            openai_api_key=OPENAI_API_KEY, 
            openai_api_base=OPENAI_API_BASE, 
            model_name='gpt-4o-mini', 
            temperature=0
        )
        content = f"「{message}」がポジティブなテキストであれば、そのままにしてください。「{message}」がネガティブなテキストであれば、ポジティブな言葉のみに変換してください。"
        messages = [
            HumanMessage(content=content),
        ]
        
        # ChatGPT APIからの応答を取得
        result = chat(messages)
        
        # 変換されたメッセージをルームグループに送信
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name, {"type": "chat_message", "message": result.content}
        )

    # ルームグループからメッセージを受信した時に呼ばれるメソッド
    def chat_message(self, event):
        # ルームグループからのメッセージを取得
        message = event["message"]
        # WebSocketにメッセージを送信
        self.send(text_data=json.dumps({"message": message}))
