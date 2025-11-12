from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone



class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Department(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name



class Employee(models.Model):
    ROLE_CHOICES = [
        ("director", "Директор"),
        ("deputy", "Заместитель директора"),
        ("head", "Руководитель отдела"),
        ("senior", "Сотрудник с повышенными правами"),
        ("staff", "Обычный сотрудник"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    position = models.CharField(max_length=255)  # текстовое поле для должности
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="staff")

    #Замещение
    delegate_to = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="delegated_from",
        verbose_name="Замещающий сотрудник",
        help_text="Кому временно переданы полномочия этого сотрудника."
    )
    delegate_until = models.DateField(
        null=True,
        blank=True,
        verbose_name="Дата окончания замещения"
    )

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
    
    def is_delegated_now(self):
        """Проверка, действует ли замещение прямо сейчас"""
        return self.delegate_to and self.delegate_until and timezone.now().date() <= self.delegate_until

    def get_delegate(self):
        """Возвращает активного замещающего, если есть"""
        if self.is_delegated_now():
            return self.delegate_to
        return None

    def get_effective_employee(self):
        """
        Возвращает фактического исполнителя (с учётом замещения)
        Например, если А делегировал Б — вернёт Б.
        """
        delegate = self.get_delegate()
        return delegate if delegate else self

    def get_active_delegate(self):
        """Вернуть актуального замещающего, если замещение активно."""
        if self.delegate_to and self.delegate_until and self.delegate_until >= timezone.now().date():
            return self.delegate_to
        return None

    # 🔸 Универсальный помощник
    def get_effective(self):
        """Если сотрудник в замещении, вернуть того, кто исполняет его обязанности."""
        delegate = self.get_active_delegate()
        return delegate if delegate else self

    @property
    def is_frozen(self):
        """Если сотрудник передал полномочия и срок ещё не истёк — он 'заморожен'."""
        return (
            self.delegate_to is not None
            and self.delegate_until is not None
            and timezone.now().date() <= self.delegate_until
        )



class EventCard(models.Model):
    PLAN_STATUS_CHOICES = [
        ("draft", "Черновик"),
        ("pending", "На согласовании"),      # после загрузки плана (исполнитель)
        ("rejected", "Отклонён"),
        ("approved", "Утверждён"),
    ]

    categories = models.ManyToManyField("Category", related_name="cards", blank=True, verbose_name="Категории")
    title = models.CharField(max_length=255, verbose_name="Название мероприятия")
    description = models.TextField(blank=True, verbose_name="Описание")
    plan_file = models.FileField(upload_to="event_plans/", null=True, blank=True, verbose_name="План мероприятия")
    plan_status = models.CharField(max_length=20, choices=PLAN_STATUS_CHOICES, default="draft")
    plan_submitted_at = models.DateTimeField(null=True, blank=True)
    plan_rejected_reason = models.TextField(null=True, blank=True)
    plan_reviewed_by_deputy = models.ForeignKey("Employee", null=True, blank=True, on_delete=models.SET_NULL, related_name="deputy_reviews")
    plan_reviewed_by_director = models.ForeignKey("Employee", null=True, blank=True, on_delete=models.SET_NULL, related_name="director_reviews")
    plan_approved_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="created_cards")
    start_date = models.DateField(default=timezone.now, verbose_name="Дата начала")

    responsible_department = models.ForeignKey("Department", null=True, blank=True, on_delete=models.SET_NULL, related_name="responsible_cards")
    shared_departments = models.ManyToManyField("Department", blank=True, related_name="shared_cards")
    end_date = models.DateField(null=True, blank=True, verbose_name="Дата окончания")
    visible = models.BooleanField(default=False, help_text="Доступна ли карточка для создания задач (после утверждения)")

    has_plan = models.BooleanField(default=False, verbose_name="С планом мероприятия")
    approvers = models.ManyToManyField(
        "Employee",
        blank=True,
        related_name="approver_cards",
        through="CardApproverOrder"
    )
    final_approver = models.ForeignKey(
        Employee, on_delete=models.PROTECT, null=True, blank=True, related_name="final_approved_cards",
        limit_choices_to={"role__in": ["deputy", "director"]},
        verbose_name="Финальный утверждающий"
    )

    current_approver_index = models.PositiveIntegerField(default=0)  # для отслеживания поочерёдности
    is_fully_approved = models.BooleanField(default=False)

    class Meta:
        ordering = ("-start_date",)

    def __str__(self):
        return self.title

    @property
    def progress(self):
        total = self.tasks.count()
        if total == 0:
            return 0
        done = self.tasks.filter(status='done').count()
        return round((done / total) * 100, 1)

    # helper: кто является "ответственным" по карточке - отдел и инициатор
    def is_user_responsible(self, user):
        """Проверить, принадлежит ли user к responsible_department"""
        try:
            emp = user.employee
        except Employee.DoesNotExist:
            return False
        return emp.department == self.responsible_department
    
     # helper: проверка может ли пользователь создавать задачи в этой карточке
    def can_user_create_task(self, user):
        # директор или заместитель всегда могут
        try:
            emp = user.employee
        except Employee.DoesNotExist:
            return False
        if emp.role in ("director", "deputy"):
            return True
        # руководитель отдела или senior сотрудник из ответственного отдела или shared departments
        if emp.role in ("head", "senior"):
            if emp.department == self.responsible_department or emp.department in self.shared_departments.all():
                return True
        # обычный сотрудник: только если в их отделе (и после утверждения) — но обычный сотрудник при создании требует утверждения
        if emp.role == "staff" and emp.department == self.responsible_department:
            # they can create but tasks will be created with status 'new' and require approval by head
            return True
        return False

class CardApproverOrder(models.Model):
    card = models.ForeignKey("EventCard", on_delete=models.CASCADE)
    employee = models.ForeignKey("Employee", on_delete=models.CASCADE)
    order = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["order"]


class Task(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('in_progress', 'В работе'),
        ('sent_for_review', 'Отправлена на согласование'),
        ('under_review', 'На рассмотрении'),
        ('done', 'Выполнена'),
        ('rejected', 'Отклонена')
    ]

    TASK_TYPE_CHOICES = [
        ("regular", "Обычная"),
        ("approval", "Согласование плана"),
        ("review", "Согласование"),

    ]

    PRIORITY_CHOICES = [
        ("normal", "Обычная"),
        ("urgent", "Срочная"),
    ] 
    
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES, default="regular")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="normal")
    card = models.ForeignKey(EventCard, on_delete=models.CASCADE, null=True, blank=True, related_name="tasks")
    title = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(verbose_name="Описание", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name="created_tasks")
    deadline = models.DateField(null=True, blank=True, verbose_name="Срок выполнения")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус")
    assigned_department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks")
    assigned_employee = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks")
    # Для ознакомления
    cc = models.ManyToManyField('Employee', blank=True, related_name="cc_tasks", verbose_name="Для ознакомления")
    # 👇 Новое поле — кому направлена задача
    recipients = models.ManyToManyField('Employee', blank=True, related_name="received_tasks", verbose_name="Адресаты")
    due_date = models.DateField(null=True, blank=True)
    google_drive_link = models.URLField(blank=True, null=True, verbose_name="Ссылка на Google Диск")
    attachment = models.FileField(upload_to="tasks/files/", blank=True, null=True, verbose_name="Вложение")
    review_comment = models.TextField(blank=True, null=True, verbose_name="Комментарий проверяющего")

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class TaskHistory(models.Model):
    ACTION_CHOICES = [
        ("created", "Создана"),
        ("assigned", "Назначена"),
        ("taken", "Взята в работу"),
        ("sent_for_review", "Отправлена на согласование"),
        ("under_review", "На рассмотрении"),
        ("rejected", "Отклонена"),
        ("redirected", "Перенаправлена"),
        ("executed", "Исполнена"),
        ("done", "Завершена"),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="history")
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.get_action_display()} — {self.task.title} ({self.timestamp:%d.%m.%Y %H:%M})"

# models.py
class TaskAttachment(models.Model):
    task = models.ForeignKey("Task", on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="tasks/execution_files/", blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    uploaded_by = models.ForeignKey("Employee", on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name if self.file else self.link or "Вложение"
