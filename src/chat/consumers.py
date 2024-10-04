import json
import requests

from django.urls import reverse
from django.conf import settings

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer

from langchain.agents import Tool, initialize_agent, AgentType
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_community.chat_models import ChatOpenAI

OPENAI_API_KEY = settings.OPENAI_API_KEY
OPENAI_API_BASE = settings.OPENAI_API_URL
LINE_NOTIFY_TOKEN = settings.LINE_NOTIFY_TOKEN

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
    # def receive(self, text_data):
    #     # 受信したメッセージをJSON形式にデコード
    #     text_data_json = json.loads(text_data)
    #     message = text_data_json["message"]
    #     flag = False
        
    #     # ChatGPT APIを使用して、メッセージをポジティブな絵文字に変換
    #     chat = ChatOpenAI(
    #         openai_api_key=OPENAI_API_KEY, 
    #         openai_api_base=OPENAI_API_BASE, 
    #         model_name='gpt-4o-mini', 
    #         temperature=0
    #     )
    #     content = f"""
    #     文字列「{message}」の感情分析をしてください。
    #     「{message}」がポジティブな文章であれば、そのまま出力してください。
    #     「{message}」がネガティブな文章であれば、「{message}」を必ずポジティブな言葉に変換したうえで、
    #     「{message}」に\"Negative Flag\"という文字列を追加してください。
    #     """
    #     messages = [
    #         HumanMessage(content=content),
    #     ]
        
    #     # ChatGPT APIからの応答を取得
    #     result = chat(messages)

    #     sentence = result.content

    #     if "Negative Flag" in sentence:
    #         flag = True
        
    #     received_message = sentence.replace("Negative Flag", "")

    #     if flag :
    #         message = f"○○さんがネガティブな文章を送信しました。"
    #         self.send_line_notify(message)
    #         filtered_text = get_last_line(received_message)
    #         received_message = filtered_text
        
    #     # 変換されたメッセージをルームグループに送信
    #     async_to_sync(self.channel_layer.group_send)(
    #         self.room_group_name, {"type": "chat_message", "message": received_message}
    #     )

    def receive(self, text_data):
        # 受信したメッセージをJSON形式にデコード
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        # flag = False
        
        # ChatGPT APIを使用して、メッセージをポジティブな絵文字に変換
        chat = ChatOpenAI(
            openai_api_key=OPENAI_API_KEY, 
            openai_api_base=OPENAI_API_BASE, 
            model_name='gpt-4o-mini', 
            temperature=0
        )
        content = (
            f"文字列「{message}」の感情分析をしてください。" +
            f"flagは「{message}」がネガティブなテキストであれば0、ポジティブなテキストであれば1を出力してください。" +
            f"flagが1だった場合、changedは「{message}」を出力してください。" +
            f"flagが0だった場合、changedは「{message}」をポジティブなテキストに変換したものを出力してください。" + 
            "以下のようなJSON形式で出力してください。" + "以下のJSON以外の文字列は出力しないでください。" +
            """
            {
                "original": "{message}", 
                "changed": "変換後のテキスト", 
                "flag": 0 or 1
            }
            """
        )

        messages = [
            HumanMessage(content=content),
        ]
        
        # ChatGPT APIからの応答を取得
        result = chat(messages)

        data = json.loads(result.content)

        if data['flag'] == 0:
            message = f"○○さんがネガティブな文章を送信しました。"
            self.send_line_notify(message)
            received_message = data['changed']
        else:
            received_message = data['original']

        # 変換されたメッセージをルームグループに送信
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name, {"type": "chat_message", "message": received_message}
        )

    # ルームグループからメッセージを受信した時に呼ばれるメソッド
    def chat_message(self, event):
        # ルームグループからのメッセージを取得
        message = event["message"]
        # WebSocketにメッセージを送信
        self.send(text_data=json.dumps({"message": message}))

    def send_line_notify(self, message):
        url = "https://notify-api.line.me/api/notify"
        headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
        payload = {"message": message}
        response = requests.post(url, headers=headers, data=payload)
        return response.status_code
    
    # def get_last_line(self, text):
    #     # 文字列を改行で分割し、最後の行を取得する
    #     lines = text.strip().split('\n')
    #     return lines[-1].strip()

    # def remove_lines_with_keyword(self, text, keyword):
    #     # 文字列を行ごとに分割し、キーワードを含む行を除外
    #     filtered_lines = [line for line in text.splitlines() if keyword not in line]
        
    #     # フィルタリングされた行を再結合して結果を返す
    #     return "\n".join(filtered_lines)
