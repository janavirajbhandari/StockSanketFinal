from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json

@csrf_exempt
@login_required
def clear_notifications(request):
    """
    Clears all unread notifications for the authenticated user.
    """
    if request.method == "POST":
        try:
            # Send a WebSocket message to clear notifications
            from .notify import notify_clients
            notify_clients([{
                "type": "clear_notifications",
                "user_id": request.user.id
            }])
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request"}, status=400) 