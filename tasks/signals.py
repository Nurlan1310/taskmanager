import os
import logging
import firebase_admin
from firebase_admin import credentials
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf import settings

# Импорт твоих моделей
from .models import Employee, Task, TaskHistory

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
# @receiver(post_save, sender=Task)
# def task_post_save_handler(sender, instance, created, **kwargs):
#     if kwargs.get('raw', False):
#         return

#     # --- А. ИСТОРИЯ (ФИО автора действия) ---
#     if created and instance.created_by_id:
#         try:
#             TaskHistory.objects.create(
#                 task_id=instance.id, 
#                 employee_id=instance.created_by_id, 
#                 action="created"
#             )
#         except Exception as e:
#             logger.error(f"Ошибка создания истории: {e}")

#     # --- Б. ИМЕННОЙ ПУШ ПРИ СОЗДАНИИ ---
#     # Отправляем уведомление только если задача создана БЕЗ согласований
#     # (если есть согласования, уведомление отправится первому согласующему в api_views.py)
#     if created and instance.assigned_employee:
#         # Проверяем, есть ли согласования
#         has_approvals = (
#             instance.status == 'send_for_approve' and 
#             instance.creation_approval_chain and 
#             len(instance.creation_approval_chain) > 0
#         )
        
#         # Отправляем уведомление только если НЕТ согласований
#         if not has_approvals and instance.task_type not in ['task_approval', 'review', 'approval']:
#             # Получаем ФИО создателя
#             try:
#                 creator_name = instance.created_by.full_name if instance.created_by else "Система"
#             except Exception:
#                 creator_name = "Система"

#             user_to_notify = instance.assigned_employee.user
#             send_task_notification(
#                 user=user_to_notify,
#                 title="Новая задача",
#                 # Формат: "Алихан Смаилов назначил вам задачу: Название"
#                 body=f"{creator_name} назначил(а) вам задачу: {instance.title}",
#                 task_id=instance.id,
#                 notification_type='task.created'
#             )
            
#             # Также уведомляем получателей (recipients)
#             if instance.recipients.exists():
#                 for recipient in instance.recipients.all():
#                     if recipient.user != user_to_notify:  # Не дублируем уведомление
#                         send_task_notification(
#                             user=recipient.user,
#                             title="Новая задача",
#                             body=f"{creator_name} добавил(а) вас в получатели задачи: {instance.title}",
#                             task_id=instance.id,
#                             notification_type='task.created'
#                         )

