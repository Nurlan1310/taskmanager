from tasks.models import Notification

def unread_notifications(request):
    if request.user.is_authenticated:
        notifs = Notification.objects.filter(user=request.user).order_by("-created_at")
        return {
            "unread_notifications": notifs.filter(is_read=False).count(),
            "last_notifications": notifs.filter(is_read=False)[:3],
        }
    return {}


