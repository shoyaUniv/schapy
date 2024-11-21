import json
import redis
import requests
import os
import io
import base64
from io import BytesIO
import traceback
import openai
from datetime import datetime
from janome.tokenizer import Tokenizer

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from django.urls import reverse
from django.conf import settings

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer

from langchain.agents import Tool, initialize_agent, AgentType
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_community.chat_models import ChatOpenAI

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload

r = redis.StrictRedis(host='redis', port=6379, db=0)  # Redisサーバーの設定

OPENAI_API_KEY = settings.OPENAI_API_KEY
OPENAI_API_BASE = settings.OPENAI_API_URL
LINE_NOTIFY_TOKEN = settings.LINE_NOTIFY_TOKEN
GOOGLE_CREDENTIALS = settings.GOOGLE_CREDENTIALS
LINE_MESSAGING_API_ACCESS_TOKEN = settings.LINE_MESSAGING_API_ACCESS_TOKEN
USER_ID = settings.USER_ID

# 変数定義
SCOPES = ['https://www.googleapis.com/auth/drive.file']
MIME_TYPE = 'application/vnd.google-apps.document'
APPLICATION_NAME = 'ipa-google-drive-api-client'

class ChatConsumer(WebsocketConsumer):
    # WebSocket接続時に呼ばれるメソッド
    def connect(self):
        try:
            # ルーム名の取得やユーザーの認証
            self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
            self.room_group_name = "chat_%s" % self.room_name
            self.room_history_name = f"room_history_{self.room_name}"

            user = self.scope["user"]
            username = user.username

            async_to_sync(self.channel_layer.group_add)(
                self.room_group_name, self.channel_name
            )
            self.accept()

            r.sadd(self.room_group_name, username)

            # 全ての接続中ユーザーを取得
            all_users = r.smembers(self.room_group_name)
            user_list = [user.decode() + '(あなた)' if user.decode() == username else user.decode() for user in all_users]

            # クライアントに送信
            self.send(text_data=json.dumps({
                'message': f'現在接続中のユーザー: {", ".join(user_list)}'
            }))
        except Exception as e:
            print(f"Error in WebSocket connect: {e}")

    # WebSocket切断時に呼ばれるメソッド
    def disconnect(self, close_code):
        # 認証されたユーザー名を取得
        user = self.scope["user"]
        username = user.username

        # ユーザー名をRedisから削除
        r.srem(self.room_group_name, username)

        # ルームグループから退出
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def receive(self, text_data):
        # 受信したメッセージをJSON形式にデコード
        text_data_json = json.loads(text_data)
        data_type = text_data_json.get("type")
        # message = text_data_json["message"]
        user_mind = False

        # 現在のユーザー名を取得
        user = self.scope["user"]
        username = user.username  # ここで送信者のユーザー名を取得

        # r.sadd(self.room_group_name, username)
        all_users = r.smembers(self.room_group_name)

        # 現在のユーザー以外の名前をフィルタリングし、bytes型をstrに変換
        otherUsers = [name.decode('utf-8') if isinstance(name, bytes) else name for name in all_users if name.decode('utf-8') != username]

        if data_type == 'text':
            message = text_data_json["message"]

            r.lpush(self.room_history_name, json.dumps({
                "text": message,
                "sender": username,
                "timestamp": datetime.now().isoformat()
            }))
            print(self.room_history_name)
            # 10件のメッセージを取得
            r.ltrim(self.room_history_name, 0, 9)
            history_msg = r.lrange(self.room_history_name, 0, 9)
            history = [json.loads(m.decode('utf-8')) for m in history_msg]
            print('history_json')
            print(history)

            # ChatGPT APIを使用して、メッセージをポジティブな絵文字に変換
            # received_data = self.gpt(message)
            received_data = self.gpt_revised(message)
            changed_message = self.gpt_changed(message, history=history)
            
            # if received_data['flag'] == 0:
            if any(received_data.values()):
                user_mind = True
                trues = ",".join([key for key, value in received_data.items() if value == True])
                if otherUsers:
                    other_users_print = ", ".join(otherUsers)
                    message = f"{username}さんが送信した文章で{trues}の項目で有害性が検知されました。\n他に{other_users_print}がいます。"
                else:
                    message = f"{username}さんが送信した文章で{trues}の項目で有害性が検知されました。"
                self.send_line_notify(USER_ID, message)
                received_message = changed_message['changed']
                # received_message = received_data['changed']
            else:
                t = Tokenizer()
                tokens = [token for token in t.tokenize(message) if token.part_of_speech.split(',')[0] != '記号']
                
                if tokens and any("命令" in token.infl_form for token in tokens if token.infl_form):
                    user_mind = True
                    # 命令性の項目が検出された場合
                    if otherUsers:
                        other_users_print = ", ".join(otherUsers)
                        message = f"{username}さんが送信した文章で命令性の項目で有害性が検知されました。\n他に{other_users_print}がいます。"
                    else:
                        message = f"{username}さんが送信した文章で命令性の項目で有害性が検知されました。"
                    self.send_line_notify(USER_ID, message)
                    received_message = changed_message['changed']
                else:
                    # 命令性の項目が検出されない、またはトークンが空の場合
                    received_message = message
                    # received_message = received_data['original']
                    # user_mind = False
                    
            # 変換されたメッセージをルームグループに送信
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name, {
                    "type": "chat_message", 
                    "message": received_message, 
                    "sender": username,
                    "user_mind": user_mind
                }
            )     
        
        elif data_type == 'image':
            image_data = text_data_json["image_data"]

            # Base64エンコードされた画像データをデコード
            format, imgstr = image_data.split(';base64,') 
            ext = format.split('/')[-1]  # 画像の拡張子を取得

            # ファイル名を生成し、画像を保存
            datetimer = datetime.now().strftime("%Y%m%d%H%M%S")
            file_name = f"{username}_{self.room_name}_{datetimer}.{ext}"
            file_path = os.path.join('chat_images', file_name)
            print(file_path)
            
            # 画像の保存
            try:
                image = ContentFile(base64.b64decode(imgstr))
                save_pa = default_storage.save(file_path, image)

                # service = self.get_service()
                # output = self.read_ocr(service, file_path, 'ja')
                # # 空行を削除
                # output_text = ''.join(filter(None, output))

                # received_data = self.gpt(output_text)
                received_data = self.gpt_image(file_path)

                # if received_data['flag'] == 0:
                if any(received_data.values()):
                    user_mind = True
                    trues = ",".join([key for key, value in received_data.items() if value == True])
                    if otherUsers:
                        other_users_print = ", ".join(otherUsers)
                        message = f"{username}さんが送信した画像で{trues}の項目で有害性が検知されました。\n他に{other_users_print}がいます。"
                        image_url = '😊'
                    else:
                        message = f"{username}さんが送信した画像で{trues}の項目で有害性が検知されました。"
                        image_url = '😊'
                    self.send_line_notify(USER_ID, message)
                else:
                    service = self.get_service()
                    output = self.read_ocr(service, file_path, 'ja')
                    output_text = ''.join(filter(None, output))
                    received_data = self.gpt_revised(output_text)
                    changed_message = self.gpt_changed(output_text)
                    if any(received_data.values()):
                        user_mind = True
                        trues = ",".join([key for key, value in received_data.items() if value == True])
                        if otherUsers:
                            other_users_print = ", ".join(otherUsers)
                            message = f"{username}さんが送信した画像で{trues}の項目で有害性が検知されました。\n他に{other_users_print}がいます。"
                            image_url = '😊'
                        else:
                            message = f"{username}さんが送信した画像で{trues}の項目で有害性が検知されました。"
                            image_url = '😊'
                        self.send_line_notify(USER_ID, message)
                    else:
                        image_url = default_storage.url(save_pa)

            except Exception as e:
                print(f"Error saving image: {e}")
                traceback.print_exc()
                return

            # 画像のURLをルームグループに送信
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name, {
                    "type": "chat_message", 
                    "message": f"{username} が画像を送信しました: {image_url}",
                    "sender": username,
                    "user_mind": user_mind
                }
            )

    # ルームグループからメッセージを受信した時に呼ばれるメソッド
    def chat_message(self, event):
        try:
            message = event["message"]
            sender = event["sender"]
            image_data = event.get("image_data")
            # user_mind = event["user_mind"]
            user_mind = event.get("user_mind", False)

            # メッセージをWebSocketに送信
            self.send(text_data=json.dumps({
                "message": message,
                "sender": sender,
                "image_data": image_data if image_data else None,
                "user_mind": user_mind
            }))
        except Exception as e:
            print(f"Error in chat_message: {e}")
            traceback.print_exc()

    # def send_line_notify(self, message):
    #     url = "https://notify-api.line.me/api/notify"
    #     headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
    #     payload = {"message": message}
    #     response = requests.post(url, headers=headers, data=payload)
    #     return response.status_code

    def send_line_notify(self, USER_ID, message):
        url = "https://api.line.me/v2/bot/message/push"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LINE_MESSAGING_API_ACCESS_TOKEN}"
        }
        payload = {
            "to": USER_ID,  # ユーザーIDまたはグループID
            "messages": [
                {
                    "type": "text",
                    "text": message
                }
            ]
        }
        response = requests.post(url, headers=headers, json=payload)
        return response.status_code
    # def gpt(self, text):
    #     chat = ChatOpenAI(
    #         openai_api_key=OPENAI_API_KEY, 
    #         openai_api_base=OPENAI_API_BASE, 
    #         model_name='gpt-4o-mini', 
    #         temperature=0
    #     )

    #     content = (
    #         f"文字列「{text}」をテキストマイニングによる、誹謗中傷テキストか、そうでないかを分析してください。" +
    #         "誹謗中傷テキストとは、悪口や根拠のない嘘等を言って、他人を傷つけたりする言葉や、名誉毀損罪や侮辱罪等に該当する言葉と定義します。" +
    #         f"flagは「{text}」が誹謗中傷テキストであれば0、そうでなければ1を出力してください。" +
    #         f"flagが1だった場合、changedは「{text}」を出力してください。" +
    #         f"flagが0だった場合、changedは「{text}」をポジティブなテキストに変換したものを出力してください。" + 
    #         "以下のjson形式で出力してください。" + "以下のjson以外の文字列は出力しないでください。" + "jsonという文字列も出力しないでください。" +
    #         """
    #         {
    #             "original": "{text}", 
    #             "changed": "変換後のテキスト", 
    #             "flag": 0 or 1
    #         }
    #         """
    #     )

    #     messages = [
    #         HumanMessage(content=content),
    #     ]

    #     # ChatGPT APIからの応答を取得
    #     result = chat(messages)
    #     print("ChatGPT API返却データ:", result.content)
    #     data = json.loads(result.content)

    #     return data
    
    def gpt_revised(self, text):
        client = openai.OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_API_BASE,
        )

        content = (
            f"小学生の会話文です。{text}について、以下のように出力してください。"
            """
            {
                "harassment": True or False,
                "harassment/threatening": True or False,
                "hate": True or False,
                "hate/threatening": True or False,
                "harassment/threatening": True or False,
                "illicit": True or False,
                "illicit/violent": True or False,
                "self-harm": True or False,
                "self-harm/intent": True or False,
                "self-harm/instructions": True or False,
                "sexual": True or False,
                "sexual/minors": True or False,
                "violence": True or False,
                "violence/graphic": True or False,
                "bullying": True or False,
                "slander": True or False,
            }
            """         
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "あなたは優秀なアシスタントです。JSON形式で日本語で返答してください。",
                },
                {"role": "user", "content": content},
            ],
        )

        data = json.loads(response.choices[0].message.content)

        return data
    
    def gpt_changed(self, text, history=None):
        client = openai.OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_API_BASE,
        )

        if history:
            history_content = "\n".join([f"会話の過去のメッセージ: {msg['text']}" for msg in history])
        else:
            history_content = ""

        print('history_content')
        print(history_content)

        content = (
            f"{history_content}\nこちらの会話文に合うように、" + 
            f"{text}をポジティブなテキストに変換してください。" +
            "以下のように出力してください。"
            """
            {
                changed: 変換した文章
            }
            """      
        )
                   
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "あなたは優秀なアシスタントです。JSON形式で日本語で返答してください。",
                },
                {"role": "user", "content": content},
            ],
        )

        data = json.loads(response.choices[0].message.content)

        return data

    def get_service(self):
        service_account_info = json.loads(base64.b64decode(settings.GOOGLE_CREDENTIALS).decode('utf-8'))
        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds)

    def read_ocr(self, service, input_file, lang='ja'):
        #サービスアカウントのメールアドレスを自分のアカウントのフォルダに設定済み
        # アップロードするファイルをGoogle Driveに送信する準備
        media_body = MediaFileUpload(input_file, mimetype=MIME_TYPE, resumable=True)

        # Google Drive上で新ファイル名を設定
        newfile = 'output.pdf'

        # アップロードするファイルのメタデータ設定
        body = {
            'name': newfile,
            'mimeType': MIME_TYPE
        }

        # Driveにファイルをアップロードし、OCRを実行
        output = service.files().create(
            body=body,
            media_body=media_body,
            ocrLanguage=lang,  # OCRの言語指定（デフォルトは英語）
        ).execute()

        # アップロードされたファイルをテキスト形式でエクスポートするリクエスト
        request = service.files().export_media(
            fileId=output['id'],  # アップロードしたファイルのID
            mimeType="text/plain"  # エクスポート形式をテキストへ指定
        )

        # エクスポートしたテキストデータを保存するファイルパス
        output_path = 'output.txt'

        # エクスポートしたデータをダウンロードし、ファイルに書き込む準備
        fh = io.FileIO(output_path, "wb")
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            # データをダウンロードする
            status, done = downloader.next_chunk()

        # Driveに一時的にアップロードしたファイル削除
        service.files().delete(fileId=output['id']).execute()

        # UTF-8エンコーディングでダウンロードしたテキストファイルを開いて行ごとに読み込む
        with open(output_path, encoding='utf-8') as f:
            # 1行目を無視する場合は[1:]
            mylist = f.read().splitlines()[1:]

        print("OCR結果:", mylist)

        # 読み込んだテキストのリスト
        return mylist
    
    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
        
    def gpt_image(self, image_path):
        client = openai.OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_API_BASE,
        )

        base64_image = self.encode_image(image_path)

        content = (
        f"{image_path}について、以下のように出力してください。"
        """
        {
            "harassment": True or False,
            "harassment/threatening": True or False,
            "hate": True or False,
            "hate/threatening": True or False,
            "harassment/threatening": True or False,
            "illicit": True or False,
            "illicit/violent": True or False,
            "self-harm": True or False,
            "self-harm/intent": True or False,
            "self-harm/instructions": True or False,
            "sexual": True or False,
            "sexual/minors": True or False,
            "violence": True or False,
            "violence/graphic": True or False,
            "bullying": True or False,
            "slander": True or False
        }
        """
        )

        response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {
            "role": "system",
            "content": "あなたは優秀なアシスタントです。JSON形式で日本語で返答してください。",
            },
            {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": content,
                },
                {
                "type": "image_url",
                "image_url": {
                    "url":  f"data:image/jpeg;base64,{base64_image}",
                    "detail": "low"
                },
                },
            ],
            }
        ],
        )

        data = json.loads(response.choices[0].message.content)

        return data
