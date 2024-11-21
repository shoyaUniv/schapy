from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import json
import requests

LINE_MESSAGING_API_ACCESS_TOKEN = settings.LINE_MESSAGING_API_ACCESS_TOKEN

# Create your views here.
def index(request):
    return render(request, "chat/index.html")

def room(request, room_name):
    return render(request, "chat/room.html", {"room_name": room_name})

@csrf_exempt
def send_line_message(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_id = data["userId"]
            message = data["message"]

            # LINE Messaging APIにリクエストを送信
            url = "https://api.line.me/v2/bot/message/push"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LINE_MESSAGING_API_ACCESS_TOKEN}"
            }
            payload = {
                "to": user_id,
                "messages": [{"type": "text", "text": message}]
            }
            response = requests.post(url, headers=headers, json=payload)
            return JsonResponse({"status": "success", "code": response.status_code})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)    