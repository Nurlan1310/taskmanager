from django.contrib.auth.models import User
from ..models import Notification


def notify(user: User, message: str, url: str = None):
    """Создаёт уведомление пользователю."""
    Notification.objects.create(
        user=user,
        message=message,
        url=url
    )
