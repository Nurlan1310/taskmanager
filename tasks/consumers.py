"""
WebSocket Consumer для отправки уведомлений в реальном времени
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Consumer для обработки WebSocket соединений и отправки уведомлений пользователям.
    Каждый пользователь подключается к своей группе: notifications_user_{user_id}
    """
    
    async def connect(self):
        """Обработка подключения WebSocket"""
        # Получаем пользователя из scope (установлен AuthMiddlewareStack)
        self.user = self.scope.get("user")
        
        if not self.user or not self.user.is_authenticated:
            # Отклоняем неавторизованные подключения
            await self.close()
            return
        
        # Создаем уникальную группу для пользователя
        self.group_name = f"notifications_user_{self.user.id}"
        
        # Присоединяемся к группе
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        # Принимаем соединение
        await self.accept()
        
        logger.info(f"WebSocket подключен: пользователь {self.user.username} (группа: {self.group_name})")
    
    async def disconnect(self, close_code):
        """Обработка отключения WebSocket"""
        if hasattr(self, 'group_name'):
            # Покидаем группу
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            logger.info(f"WebSocket отключен: пользователь {self.user.username if self.user else 'Unknown'}")
    
    async def receive(self, text_data):
        """Обработка сообщений от клиента (опционально, для ping/pong)"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                # Отправляем pong для поддержания соединения
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'message': 'ok'
                }))
        except json.JSONDecodeError:
            logger.warning(f"Неверный JSON от клиента: {text_data}")
    
    async def notification_message(self, event):
        """
        Обработчик для отправки уведомления клиенту.
        Вызывается когда в группу отправляется сообщение через channel_layer.group_send()
        """
        try:
            notification_type = event.get('data', {}).get('type', 'unknown')
            notification_id = event.get('data', {}).get('id', 'N/A')
            
            logger.info(
                f"Отправка уведомления пользователю {self.user.id if self.user else 'Unknown'}: "
                f"тип={notification_type}, ID={notification_id}"
            )
            
            # Отправляем уведомление клиенту
            message_data = {
                'type': 'notification',
                'data': event['data']
            }
            
            await self.send(text_data=json.dumps(message_data))
            
            logger.debug(
                f"Уведомление успешно отправлено пользователю {self.user.id if self.user else 'Unknown'}: "
                f"тип={notification_type}, ID={notification_id}"
            )
        except Exception as e:
            logger.error(
                f"Ошибка при отправке уведомления пользователю {self.user.id if self.user else 'Unknown'}: {e}",
                exc_info=True
            )