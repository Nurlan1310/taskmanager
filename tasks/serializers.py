from rest_framework import serializers
from django.contrib.auth.models import User
from urllib.parse import unquote
import os
import logging
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q

# 🔥 Импортируем все модели (включая CardApproverOrder)
from .models import (
    Task, EventCard, Employee, Department, Category, 
    TaskHistory, TaskAttachment, TaskComment, Notification, FCMDevice, CardApproverOrder
)

# =========================================================
# Вспомогательные сериализаторы
# =========================================================

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['username']


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'priority']


class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    full_name_complete = serializers.CharField(read_only=True)
    photo = serializers.ImageField(read_only=True)

    class Meta:
        model = Employee
        fields = ['id', 'user', 'full_name', 'full_name_complete', 'firstname', 'lastname', 'middlename', 'position', 'department', 'role', 'photo', 'internal_phone', 'external_phone']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class TaskHistorySerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = TaskHistory
        fields = ['id', 'action', 'action_display', 'employee', 'comment', 'timestamp']


class TaskAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = EmployeeSerializer(read_only=True)
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = TaskAttachment
        fields = ['id', 'file', 'file_name', 'link', 'uploaded_by', 'uploaded_at']
        read_only_fields = ['uploaded_by', 'uploaded_at', 'file_name']
    
    def get_file_name(self, obj):
        if obj.file:
            file_path = obj.file.name
            file_name = os.path.basename(file_path)
            try:
                decoded = unquote(file_name, encoding='utf-8')
                return decoded if '%' not in decoded else unquote(decoded, encoding='utf-8')
            except:
                return file_name
        return None

# =========================================================
# ГЛАВНЫЙ СЕРИАЛИЗАТОР ЗАДАЧ (Исправленный)
# =========================================================

class TaskSerializer(serializers.ModelSerializer):
    created_by = EmployeeSerializer(read_only=True)
    assigned_employee = EmployeeSerializer(read_only=True)
    assigned_department = DepartmentSerializer(read_only=True)
    recipients = EmployeeSerializer(many=True, read_only=True)
    redirected_by = EmployeeSerializer(read_only=True)
    redirect_chain_employees = serializers.SerializerMethodField()
    
    # 🔥 НОВОЕ: Умные поля для ФИО и Отдела (убираем "Без отдела")
    assigned_employee_name = serializers.SerializerMethodField()
    assigned_department_name = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    
    card = serializers.PrimaryKeyRelatedField(queryset=EventCard.objects.all(), required=False, allow_null=True)
    card_title = serializers.SerializerMethodField()
    
    task_type_display = serializers.CharField(source="get_task_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    is_urgent = serializers.BooleanField(read_only=True)

    history = TaskHistorySerializer(many=True, read_only=True)
    attachments = serializers.SerializerMethodField()
    
    # Поля для записи и фильтрации (IDs)
    recipients_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Employee.objects.all(), source='recipients', write_only=True, required=False
    )
    assigned_employee_id = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(), source='assigned_employee', write_only=True, required=False, allow_null=True
    )
    # Нужно для фронта, чтобы быстро фильтровать по отделу
    assigned_department_id = serializers.IntegerField(source='assigned_department.id', read_only=True, allow_null=True)
    
    # Поля согласования создания
    is_according_to_plan = serializers.BooleanField(required=False)
    creation_approval_chain = serializers.ListField(
        child=serializers.IntegerField(),
        read_only=True,
    )
    current_approval_index = serializers.IntegerField(read_only=True, allow_null=True)
    parent_task_id = serializers.IntegerField(source='parent_task.id', read_only=True, allow_null=True)
    relation_type = serializers.CharField(read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'status', 'status_display', 
            'task_type', 'task_type_display', 'priority', 'priority_display', 'is_urgent',
            'is_according_to_plan', 'creation_approval_chain', 'current_approval_index',
            'parent_task_id', 'relation_type',
            'created_at', 'due_date', 'created_by', 'created_by_name',
            'assigned_employee', 'assigned_employee_id', 'assigned_employee_name',
            'assigned_department', 'assigned_department_id', 'assigned_department_name',
            'recipients', 'recipients_ids', 'card', 'card_title',
            'google_drive_link', 'review_comment', 'history', 'attachments', 'redirected_by', 'redirect_chain', 'redirect_chain_employees', 'current_reviewer', 'current_approver'
        ]
        read_only_fields = ['created_at']

    # ✅ ИСПРАВЛЕНИЕ: Показываем ФИО или "Не назначен"
    def get_assigned_employee_name(self, obj):
        if obj.assigned_employee:
            return obj.assigned_employee.full_name
        return "Исполнитель не назначен"

    # ✅ ИСПРАВЛЕНИЕ: Убираем "Без отдела", возвращаем пусто, если его нет
    def get_assigned_department_name(self, obj):
        if obj.assigned_department:
            return obj.assigned_department.name
        # Fallback: если отдел не привязан к задаче, берем отдел сотрудника
        if obj.assigned_employee and obj.assigned_employee.department:
            return obj.assigned_employee.department.name
        return ""

    def get_card_title(self, obj):
        return obj.card.title if obj.card else None

    def get_attachments(self, obj):
        return TaskAttachmentSerializer(obj.attachments.all(), many=True).data
    
    def get_redirect_chain_employees(self, obj):
        """Возвращает список сотрудников из цепочки перенаправлений в порядке перенаправления"""
        if not obj.redirect_chain:
            return []
        # Получаем сотрудников по ID из цепочки, сохраняя порядок из списка
        redirect_employees_dict = {
            emp.id: EmployeeSerializer(emp).data 
            for emp in Employee.objects.filter(id__in=obj.redirect_chain)
        }
        # Возвращаем список в порядке из redirect_chain
        return [
            redirect_employees_dict[emp_id] 
            for emp_id in obj.redirect_chain 
            if emp_id in redirect_employees_dict
        ]
    
    current_reviewer = serializers.SerializerMethodField()
    current_approver = serializers.SerializerMethodField()
    
    def get_current_reviewer(self, obj):
        """Возвращает текущего проверяющего для задачи в статусе sent_for_review или under_review"""
        if obj.status not in ('sent_for_review', 'under_review'):
            return None
        
        # Ищем активную задачу на проверку для этой задачи
        import re
        review_task = Task.objects.filter(
            card=obj.card,
            task_type="review",
            status__in=('new', 'in_progress'),
            description__icontains=f"[orig_task_id:{obj.id}]"
        ).select_related('assigned_employee').order_by("-created_at").first()
        
        if review_task and review_task.assigned_employee:
            return EmployeeSerializer(review_task.assigned_employee).data
        return None
    
    def get_current_approver(self, obj):
        """Возвращает текущего согласующего для задачи в статусе send_for_approve"""
        if obj.status != 'send_for_approve':
            return None
        
        # Ищем активную задачу на согласование создания для этой задачи
        approval_task = Task.objects.filter(
            parent_task=obj,
            task_type="task_approval",
            status__in=('new', 'in_progress')
        ).select_related('assigned_employee').order_by("-created_at").first()
        
        if approval_task and approval_task.assigned_employee:
            return EmployeeSerializer(approval_task.assigned_employee).data
        return None

    # Логика создания (сохранена полностью как у твоего друга)
    def create(self, validated_data):
        recipients = validated_data.pop('recipients', [])
        # Удаляем google_drive_link из validated_data, так как он будет обработан в api_views для создания TaskAttachment
        validated_data.pop('google_drive_link', None)
        if 'created_by' not in validated_data:
            raise serializers.ValidationError({'created_by': 'Поле created_by обязательно.'})
        
        if not validated_data.get('assigned_employee') and recipients:
            validated_data['assigned_employee'] = recipients[0]
        
        try:
            task = Task.objects.create(**validated_data)
        except Exception as e:
            logging.getLogger(__name__).error(f"Ошибка создания задачи: {e}")
            raise serializers.ValidationError({'error': str(e)})
        
        if recipients:
            task.recipients.set(recipients)
        return task


class EventCardSerializer(serializers.ModelSerializer):
    created_by = EmployeeSerializer(read_only=True)
    responsible_department = DepartmentSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    shared_departments = DepartmentSerializer(many=True, read_only=True)
    final_approver = EmployeeSerializer(read_only=True)
    approvers = EmployeeSerializer(many=True, read_only=True)
    
    responsible_department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source='responsible_department', write_only=True, required=False, allow_null=True
    )
    final_approver_id = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.filter(role__in=['director', 'deputy']), source='final_approver', write_only=True, required=False, allow_null=True
    )
    categories_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.all(), source='categories', write_only=True, required=False
    )
    shared_departments_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Department.objects.all(), source='shared_departments', write_only=True, required=False
    )
    approvers_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False, allow_empty=True
    )

    is_active = serializers.SerializerMethodField()
    progress = serializers.ReadOnlyField()
    
    # Поля для общих задач (все задачи карточки)
    done_count = serializers.SerializerMethodField()
    total_tasks = serializers.SerializerMethodField()
    
    # Поля для задач пользователя
    user_active_count = serializers.SerializerMethodField()
    user_urgent_count = serializers.SerializerMethodField()
    user_approval_count = serializers.SerializerMethodField()
    user_total_tasks = serializers.SerializerMethodField()
    user_done_tasks = serializers.SerializerMethodField()
    user_progress = serializers.SerializerMethodField()
    
    # Поля для задач отдела
    department_done_tasks = serializers.SerializerMethodField()
    department_total_tasks = serializers.SerializerMethodField()
    department_progress = serializers.SerializerMethodField()

    class Meta:
        model = EventCard
        fields = [
            'id', 'title', 'description', 'start_date', 'end_date',
            'created_by', 'responsible_department', 'responsible_department_id', 'categories', 'categories_ids',
            'shared_departments', 'shared_departments_ids', 'plan_status', 'plan_file',
            'final_approver', 'final_approver_id', 'approvers', 'approvers_ids', 'has_plan', 'visible',
            'progress', 'is_active', 'plan_submitted_at', 'plan_approved_at', 'plan_rejected_reason',
            'current_approver_index', 'is_fully_approved',
            'done_count', 'total_tasks', 'user_active_count', 'user_urgent_count', 
            'user_approval_count', 'user_total_tasks', 'user_done_tasks',
            'user_progress', 'department_done_tasks', 'department_total_tasks', 'department_progress'
        ]
        read_only_fields = ['created_by', 'progress', 'plan_submitted_at', 'plan_approved_at', 
                           'plan_rejected_reason', 'current_approver_index', 'is_fully_approved']

    def get_is_active(self, obj):
        today = timezone.now().date()
        if not obj.end_date:
            return obj.start_date <= today
        return obj.start_date <= today <= obj.end_date
    
    def get_done_count(self, obj):
        """Количество выполненных задач (все задачи карточки)"""
        return obj.tasks.filter(status='done').count()
    
    def get_total_tasks(self, obj):
        """Общее количество задач (все задачи карточки)"""
        return obj.tasks.count()
    
    def _get_user_tasks(self, obj):
        """Получить задачи пользователя для данной карточки"""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            return Task.objects.none()
        
        try:
            employee = request.user.employee
        except Employee.DoesNotExist:
            return Task.objects.none()
        
        effective_employee = employee.get_effective_employee()
        
        # Задачи пользователя в данной карточке
        return obj.tasks.filter(
            Q(assigned_employee=effective_employee) |
            Q(recipients=effective_employee)
        ).distinct()
    
    def get_user_active_count(self, obj):
        """Количество активных задач пользователя"""
        user_tasks = self._get_user_tasks(obj)
        return user_tasks.exclude(status='done').count()
    
    def get_user_urgent_count(self, obj):
        """Количество срочных задач пользователя"""
        user_tasks = self._get_user_tasks(obj)
        now = timezone.now()
        urgent_deadline = now + timedelta(days=3)
        return user_tasks.filter(
            priority='urgent',
            due_date__lte=urgent_deadline,
            due_date__isnull=False
        ).exclude(status='done').count()
    
    def get_user_approval_count(self, obj):
        """Количество задач на согласование пользователя"""
        user_tasks = self._get_user_tasks(obj)
        return user_tasks.filter(
            task_type__in=['approval', 'review', 'task_approval']
        ).exclude(status='done').count()
    
    def get_user_total_tasks(self, obj):
        """Общее количество задач пользователя"""
        return self._get_user_tasks(obj).count()
    
    def get_user_done_tasks(self, obj):
        """Количество выполненных задач пользователя"""
        user_tasks = self._get_user_tasks(obj)
        return user_tasks.filter(status='done').count()
    
    def _get_department_tasks(self, obj):
        """Получить задачи отдела для данной карточки"""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            return Task.objects.none()
        
        try:
            employee = request.user.employee
        except Employee.DoesNotExist:
            return Task.objects.none()
        
        effective_employee = employee.get_effective_employee()
        
        # Если у пользователя нет отдела, возвращаем пустой queryset
        if not effective_employee.department:
            return Task.objects.none()
        
        # Задачи отдела в данной карточке
        return obj.tasks.filter(
            Q(assigned_department=effective_employee.department) |
            Q(assigned_employee__department=effective_employee.department)
        ).distinct()
    
    def get_department_done_tasks(self, obj):
        """Количество выполненных задач отдела"""
        department_tasks = self._get_department_tasks(obj)
        return department_tasks.filter(status='done').count()
    
    def get_department_total_tasks(self, obj):
        """Общее количество задач отдела"""
        return self._get_department_tasks(obj).count()
    
    def get_department_progress(self, obj):
        """Прогресс отдела в процентах"""
        department_tasks = self._get_department_tasks(obj)
        total = department_tasks.count()
        if total == 0:
            return 0
        done = department_tasks.filter(status='done').count()
        return round((done / total) * 100)
    
    def get_user_progress(self, obj):
        """Прогресс пользователя в процентах"""
        user_tasks = self._get_user_tasks(obj)
        total = user_tasks.count()
        if total == 0:
            return 0
        done = user_tasks.filter(status='done').count()
        return round((done / total) * 100)

    def create(self, validated_data):
        approvers_ids = validated_data.pop('approvers_ids', [])
        card = super().create(validated_data)
        for idx, emp_id in enumerate(approvers_ids):
            try:
                emp = Employee.objects.get(id=emp_id)
                CardApproverOrder.objects.create(card=card, employee=emp, order=idx)
            except Employee.DoesNotExist: continue
        return card

    def update(self, instance, validated_data):
        approvers_ids = validated_data.pop('approvers_ids', None)
        card = super().update(instance, validated_data)
        if approvers_ids is not None:
            CardApproverOrder.objects.filter(card=card).delete()
            for idx, emp_id in enumerate(approvers_ids):
                try:
                    emp = Employee.objects.get(id=emp_id)
                    CardApproverOrder.objects.create(card=card, employee=emp, order=idx)
                except Employee.DoesNotExist: continue
        return card


class EventCardDetailSerializer(EventCardSerializer):
    tasks = TaskSerializer(many=True, read_only=True)
    class Meta(EventCardSerializer.Meta):
        fields = EventCardSerializer.Meta.fields + ['tasks']


class TaskCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True)

    class Meta:
        model = TaskComment
        fields = ['id', 'task', 'author', 'author_name', 'text', 'created_at']
        read_only_fields = ['id', 'author', 'created_at', 'task']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'url', 'created_at', 'is_read']


class FCMDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMDevice
        fields = ['id', 'token', 'platform']
        read_only_fields = ['id', 'token']