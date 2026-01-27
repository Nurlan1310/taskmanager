"""
Утилита для отправки WebSocket уведомлений в реальном времени
"""
import logging
import os
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
from .models import Notification, FCMDevice

logger = logging.getLogger(__name__)

# Инициализация Firebase (если еще не инициализирован)
if not firebase_admin._apps:
    try:
        cred_path = str(settings.FIREBASE_SERVICE_ACCOUNT_FILE)
        if os.path.exists(cred_path):
            cred = firebase_admin.credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase успешно инициализирован.")
        else:
            logger.error(f"Файл ключей Firebase не найден: {cred_path}")
    except Exception as e:
        logger.error(f"Ошибка при инициализации Firebase: {e}")


def send_websocket_notification(user_id, notification_data):
    """
    Отправляет WebSocket уведомление конкретному пользователю
    
    Args:
        user_id: ID пользователя (User.id)
        notification_data: Словарь с данными уведомления:
            {
                'id': int,  # ID уведомления из БД
                'message': str,  # Текст уведомления
                'url': str,  # URL для перехода
                'type': str,  # Тип события (task.created, task.assigned, etc.)
                'task_id': int,  # ID задачи (опционально)
                'created_at': str,  # Время создания
            }
    """
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning(f"Channel layer не настроен. WebSocket уведомление пользователю {user_id} не будет отправлено.")
            return
        
        group_name = f"notifications_user_{user_id}"
        
        # Отправляем сообщение в группу пользователя
        # Используем async_to_sync для синхронного вызова из синхронного кода
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'notification_message',
                'data': notification_data
            }
        )
        
        logger.info(
            f"WebSocket уведомление отправлено пользователю {user_id} "
            f"(тип: {notification_data.get('type', 'unknown')}, "
            f"ID уведомления: {notification_data.get('id', 'N/A')})"
        )
        
    except Exception as e:
        logger.error(
            f"Ошибка при отправке WebSocket уведомления пользователю {user_id}: {e}",
            exc_info=True  # Добавляем полный traceback для отладки
        )


def send_websocket_notification_to_users(user_ids, notification_data):
    """
    Отправляет WebSocket уведомление нескольким пользователям
    
    Args:
        user_ids: Список ID пользователей
        notification_data: Словарь с данными уведомления
    """
    for user_id in user_ids:
        send_websocket_notification(user_id, notification_data)


def send_task_notification(user, title, body, task_id, notification_type='task_update', url=None):
    """
    Записывает уведомление в базу, отправляет WebSocket уведомление и именной Push через Firebase
    
    Args:
        user: Пользователь (User)
        title: Заголовок уведомления
        body: Текст уведомления
        task_id: ID задачи
        notification_type: Тип события (task.created, task.assigned, task.status_changed, etc.)
        url: Опциональный URL для уведомления (если не указан, используется /tasks/{task_id})
    """
    try:
        # Определяем URL для уведомления
        notification_url = url if url else f"/tasks/{task_id}"
        
        # 1. Запись в базу (для списка в приложении)
        notification = Notification.objects.create(
            user=user,
            message=body,
            url=notification_url  # Без слэша в конце для правильной навигации
        )

        # 2. Отправка WebSocket уведомления в реальном времени
        try:
            send_websocket_notification(
                user_id=user.id,
                notification_data={
                    'id': notification.id,
                    'message': body,
                    'url': notification_url,  # Без слэша в конце для правильной навигации
                    'type': notification_type,
                    'task_id': task_id,
                    'created_at': notification.created_at.isoformat(),
                    'is_read': False,
                }
            )
        except Exception as e:
            logger.warning(f"Ошибка отправки WebSocket уведомления: {e}")

        # 3. Рассылка по всем устройствам пользователя (FCM для мобильных)
        devices = FCMDevice.objects.filter(user=user)
        
        if not devices.exists():
            logger.info(f"У {user.username} нет активных девайсов.")
            return

        for device in devices:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    token=device.token,
                    data={
                        "task_id": str(task_id),
                        "type": notification_type
                    }
                )
                response = messaging.send(message)
                logger.info(f"Пуш отправлен успешно: {response}")
                
            except Exception as e:
                logger.warning(f"Ошибка токена {device.token}: {e}")
                if "registration-token-not-registered" in str(e).lower():
                    device.delete()
    
    except Exception as e:
        logger.error(f"Ошибка в системе уведомлений: {e}")