from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
from core.models import ChatMessage
from core.chatbox import GeminiChatService

@login_required
@require_POST
@csrf_exempt
def chat_message_api(request):
    """API endpoint nhận tin nhắn từ frontend"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({'error': 'Message không được để trống'}, status=400)
        
        # Lưu tin nhắn của user
        ChatMessage.objects.create(
            user=request.user,
            message=user_message,
            role='USER'
        )
        
        # Gọi Gemini Service
        service = GeminiChatService()
        bot_response = service.chat(user_message, request.user)
        
        # Lưu phản hồi của bot
        ChatMessage.objects.create(
            user=request.user,
            message=bot_response,
            role='BOT'
        )
        
        return JsonResponse({
            'status': 'success',
            'message': bot_response
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_chat_history(request):
    """Lấy lịch sử chat"""
    messages = ChatMessage.objects.filter(user=request.user).values('role', 'message', 'created_at')[:20]
    return JsonResponse({
        'status': 'success',
        'messages': list(messages)
    })

@login_required
def get_chat_greeting(request):
    """Lấy greeting message khi mở chat lần đầu"""
    first_name = request.user.first_name or "bạn"
    greeting = f"Xin chào {first_name} ! ,tôi là trợ lý ảo của thư viện, tôi có thể giúp gì cho bạn? "
    return JsonResponse({'message': greeting})