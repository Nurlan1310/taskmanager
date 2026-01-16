import os
import logging
import firebase_admin
from firebase_admin import credentials, messaging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf import settings

# Импорт твоих моделей
from .models import Employee, Task, TaskHistory, Notification, FCMDevice, TaskComment

logger = logging.getLogger(__name__)

# ==========================================
# 🚀 ИНИЦИАЛИЗАЦИЯ FIREBASE
# ==========================================
if not firebase_admin._apps:
    try:
        cred_path = str(settings.FIREBASE_SERVICE_ACCOUNT_FILE)
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase успешно инициализирован.")
        else:
            logger.error(f"Файл ключей Firebase не найден: {cred_path}")
    except Exception as e:
        logger.error(f"Ошибка при инициализации Firebase: {e}")


# ==========================================
# 1. ПРОФИЛИ СОТРУДНИКОВ (Код друга)
# ==========================================
@receiver(post_save, sender=User)
def create_employee_profile(sender, instance, created, **kwargs):
    if created:
        Employee.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_employee_profile(sender, instance, **kwargs):
    if hasattr(instance, 'employee'):
        instance.employee.save()


# ==========================================
# 2. ПРОГРЕСС КАРТОЧКИ (Код друга)
# ==========================================
@receiver([post_save, post_delete], sender=Task)
def update_card_progress(sender, instance, **kwargs):
    if instance.card:
        try:
            _ = instance.card.progress
        except Exception as e:
            logger.error(f"Ошибка прогресса карточки: {e}")


# ==========================================
# 3. ИСТОРИЯ И ИМЕННЫЕ ПУШИ ДЛЯ ЗАДАЧ
# ==========================================
@receiver(post_save, sender=Task)
def task_post_save_handler(sender, instance, created, **kwargs):
    if kwargs.get('raw', False):
        return

    # --- А. ИСТОРИЯ (ФИО автора действия) ---
    if created and instance.created_by_id:
        try:
            TaskHistory.objects.create(
                task_id=instance.id, 
                employee_id=instance.created_by_id, 
                action="created"
            )
        except Exception as e:
            logger.error(f"Ошибка создания истории: {e}")

    # --- Б. ИМЕННОЙ ПУШ ПРИ СОЗДАНИИ ---
    if created and instance.assigned_employee:
        # Получаем ФИО создателя
        try:
            creator_name = instance.created_by.full_name if instance.created_by else "Система"
        except Exception:
            creator_name = "Система"

        user_to_notify = instance.assigned_employee.user
        send_task_notification(
            user=user_to_notify,
            title="Новая задача",
            # Формат: "Алихан Смаилов назначил вам задачу: Название"
            body=f"{creator_name} назначил(а) вам задачу: {instance.title}",
            task_id=instance.id
        )


# ==========================================
# 4. ИМЕННЫЕ ПУШИ ДЛЯ КОММЕНТАРИЕВ
# ==========================================
@receiver(post_save, sender=TaskComment)
def comment_post_save_handler(sender, instance, created, **kwargs):
    if created:
        task = instance.task
        author = instance.author  # Это модель Employee
        
        # Определяем получателя (если пишет не исполнитель — шлем исполнителю)
        recipient_user = None
        if task.assigned_employee and author != task.assigned_employee:
            recipient_user = task.assigned_employee.user
        elif task.created_by and author != task.created_by:
            recipient_user = task.created_by.user

        if recipient_user:
            send_task_notification(
                user=recipient_user,
                title="Новый комментарий",
                # Формат: "Иван Иванов: Текст комментария..."
                body=f"{author.full_name}: {instance.text[:50]}...",
                task_id=task.id
            )


# ==========================================
# 🛠 ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ОТПРАВКИ
# ==========================================
def send_task_notification(user, title, body, task_id):
    """Записывает уведомление в базу и шлет именной Push через Firebase"""
    try:
        # 1. Запись в базу (для списка в приложении)
        Notification.objects.create(
            user=user,
            message=body,
            url=f"/task/{task_id}/"
        )

        # 2. Рассылка по всем устройствам пользователя
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
                        "type": "task_update"
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