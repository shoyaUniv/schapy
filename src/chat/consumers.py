import json
import redis
import requests
import os
import io
import base64
import pytesseract
from PIL import Image
from io import BytesIO
import traceback

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

            user = self.scope["user"]
            username = user.username

            async_to_sync(self.channel_layer.group_add)(
                self.room_group_name, self.channel_name
            )
            self.accept()

            r.sadd(self.room_group_name, username)

            all_users = r.smembers(self.room_group_name)
            self.send(text_data=json.dumps({
                'message': f'現在接続中のユーザー: {", ".join(user.decode() for user in all_users)}'
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

        # 現在のユーザー名を取得
        user = self.scope["user"]
        username = user.username  # ここで送信者のユーザー名を取得

        if data_type == 'text':
            message = text_data_json["message"]
            # ChatGPT APIを使用して、メッセージをポジティブな絵文字に変換
            received_data = self.gpt(message)
            
            if received_data['flag'] == 0:
                message = f"{username}さんがネガティブな文章を送信しました。"
                self.send_line_notify(message)
                received_message = received_data['changed']
            else:
                received_message = received_data['original']
            
            # 変換されたメッセージをルームグループに送信
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name, {"type": "chat_message", "message": received_message}
            )     
        
        elif data_type == 'image':
            image_data = text_data_json["image_data"]

            # Base64エンコードされた画像データをデコード
            format, imgstr = image_data.split(';base64,') 
            ext = format.split('/')[-1]  # 画像の拡張子を取得

            # ファイル名を生成し、画像を保存
            file_name = f"{username}_{self.room_name}.{ext}"
            file_path = os.path.join('chat_images', file_name)
            
            # 画像の保存
            try:
                image = ContentFile(base64.b64decode(imgstr))
                save_pa = default_storage.save(file_path, image)

                service = self.get_service()
                output = self.read_ocr(service, file_path, 'ja')
                # 空行を削除
                output_text = ''.join(filter(None, output))

                # Tesseractを使用して画像からテキストを抽出
                # image_by = default_storage.open(file_path).read()  # 保存された画像を読み込む
                # pi_image = Image.open(BytesIO(image_by))  # PILで画像を開く
                # ex_text = pytesseract.image_to_string(pi_image)  # OCR処理

                received_data = self.gpt(output_text)

                if received_data['flag'] == 0:
                    message = f"{username}さんがネガティブな画像を送信しました。"
                    self.send_line_notify(message)
                    image_url = '😊'
                else:
                    image_url = default_storage.url(save_pa)

            except Exception as e:
                print(f"Error saving image: {e}")
                traceback.print_exc()
                return

            # 画像のURLをルームグループに送信
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name, {"type": "chat_message", "message": f"{username} が画像を送信しました: {image_url}"}
            )

    # ルームグループからメッセージを受信した時に呼ばれるメソッド
    def chat_message(self, event):
        # ルームグループからのメッセージを取得
        message = event["message"]
        image_data = event.get("image_data", None)
        # 画像データがあるか確認
        # WebSocketにテキストと画像データをJSON形式で送信
        if image_data:
            self.send(text_data=json.dumps({
                "message": message,
                # 画像データを送信
                "image_data": image_data
            }))
        else:
            self.send(text_data=json.dumps({
                "message": message
            }))

    def send_line_notify(self, message):
        url = "https://notify-api.line.me/api/notify"
        headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
        payload = {"message": message}
        response = requests.post(url, headers=headers, data=payload)
        return response.status_code
    
    def gpt(self, text):
        chat = ChatOpenAI(
            openai_api_key=OPENAI_API_KEY, 
            openai_api_base=OPENAI_API_BASE, 
            model_name='gpt-4o-mini', 
            temperature=0
        )

        content = (
            f"文字列「{text}」をテキストマイニングによる、誹謗中傷テキストか、そうでないかを分析してください。" +
            "誹謗中傷テキストとは、悪口や根拠のない嘘等を言って、他人を傷つけたりする言葉や、名誉毀損罪や侮辱罪等に該当する言葉と定義します。" +
            f"flagは「{text}」が誹謗中傷テキストであれば0、そうでなければ1を出力してください。" +
            f"flagが1だった場合、changedは「{text}」を出力してください。" +
            f"flagが0だった場合、changedは「{text}」をポジティブなテキストに変換したものを出力してください。" + 
            "以下のjson形式で出力してください。" + "以下のjson以外の文字列は出力しないでください。" + "jsonという文字列も出力しないでください。" +
            """
            {
                "original": "{text}", 
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

        return data

    def get_service(self):
        # サービスアカウントのJSONファイルのパスを環境変数から取得
        google_drive_api_json_path = os.getenv('GOOGLE_DRIVE_API_JSON_PATH')

        # サービスアカウント認証を使って認証情報を取得
        creds = Credentials.from_service_account_file(google_drive_api_json_path, scopes=SCOPES)

        # Google Drive APIクライアントを作成
        service = build('drive', 'v3', credentials=creds)
        
        return service

    def read_ocr(self, service, input_file, lang='en'):
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

        # 読み込んだテキストのリスト
        return mylist
