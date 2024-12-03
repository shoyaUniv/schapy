from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import json
import requests
import redis

r = redis.StrictRedis(host='redis', port=6379, db=0)

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

def delete_redis_message(request):
    if request.method == 'POST':
        room_name = request.POST.get('room_name')
        if not room_name:
            return JsonResponse({'error': 'room_name is required'}, status=400)

        room_history_name = f"room_history_{room_name}"
        try:
            # 削除前にRedisのリストを確認
            current_history = r.lrange(room_history_name, 0, -1)
            if not current_history:
                return JsonResponse({'error': f'No messages found for {room_name}'}, status=404)

            # 最後のメッセージを削除
            deleted_message = r.rpop(room_history_name)
            if deleted_message:
                return JsonResponse({
                    'message': 'Last message deleted successfully',
                    'deleted_message': deleted_message.decode('utf-8'),
                    'remaining_messages': [m.decode('utf-8') for m in r.lrange(room_history_name, 0, -1)]
                })
            else:
                return JsonResponse({'error': 'No messages to delete'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid HTTP method'}, status=405)