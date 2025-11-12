from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Employee, Task, TaskHistory

@receiver(post_save, sender=User)
def create_employee_profile(sender, instance, created, **kwargs):
    if created:
        Employee.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_employee_profile(sender, instance, **kwargs):
    instance.employee.save()

@receiver([post_save, post_delete], sender=Task)
def update_card_progress(sender, instance, **kwargs):
    """После сохранения или удаления задачи пересчитываем прогресс карточки"""
    if instance.card:
        instance.card.progress

@receiver(post_save, sender=Task)
def create_task_history(sender, instance, created, **kwargs):
    if created:
        TaskHistory.objects.create(task=instance, employee=instance.created_by, action="created")