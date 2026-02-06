from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta  # 👈 Нужно для проверки срочности


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
    shortname = models.CharField(max_length=255, blank=True, null=True, verbose_name="Короткое название")
    priority = models.IntegerField(default=0, verbose_name="Приоритет", help_text="Чем меньше число, тем выше приоритет. Используется для сортировки отделов.")

    class Meta:
        ordering = ['priority', 'name']
        verbose_name = "Отдел"
        verbose_name_plural = "Отделы"

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
    photo = models.ImageField(upload_to="profile_photos/", null=True, blank=True, verbose_name="Фото профиля")
    internal_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Внутренний телефон", help_text="Внутренний номер телефона сотрудника")
    external_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Рабочий номер", help_text="Рабочий номер телефона сотрудника")
    
    # ФИО сотрудника
    firstname = models.CharField(max_length=150, blank=True, null=True, verbose_name="Имя", help_text="Имя сотрудника")
    lastname = models.CharField(max_length=150, blank=True, null=True, verbose_name="Отчество", help_text="Отчество сотрудника")
    middlename = models.CharField(max_length=150, blank=True, null=True, verbose_name="Фамилия", help_text="Фамилия сотрудника")

    # Замещение
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

    # 🔥 ДОБАВЛЕНО (нужно для API): Свойство для получения ФИО в формате "Фамилия И.О."
    @property
    def full_name(self):
        """Возвращает ФИО в формате 'Фамилия И.О.' или username, если данные не заполнены."""
        if self.middlename or self.firstname or self.lastname:
            parts = []
            if self.middlename:
                parts.append(self.middlename)
            if self.firstname:
                initial = self.firstname[0].upper() + "."
                parts.append(initial)
            if self.lastname:
                initial = self.lastname[0].upper() + "."
                parts.append(initial)
            if parts:
                return " ".join(parts)
        # Fallback на username, если поля Employee не заполнены
        return self.user.username
    
    # 🔥 ДОБАВЛЕНО: Свойство для получения полного ФИО в формате "Фамилия Имя Отчество"
    @property
    def full_name_complete(self):
        """Возвращает полное ФИО в формате 'Фамилия Имя Отчество' или username, если данные не заполнены."""
        if self.middlename or self.firstname or self.lastname:
            parts = []
            if self.middlename:
                parts.append(self.middlename)
            if self.firstname:
                parts.append(self.firstname)
            if self.lastname:
                parts.append(self.lastname)
            if parts:
                return " ".join(parts)
        # Fallback на username, если поля Employee не заполнены
        return self.user.username

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"
    
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

    # 🔥 ДОБАВЛЕНО (нужно для уведомлений)
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("card_detail", args=[self.id])

    @property
    def progress(self):
        total = self.tasks.count()
        if total == 0:
            return 0
        done = self.tasks.filter(status='done').count()
        return round((done / total) * 100)

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
        ('sent_for_review', 'Отправлено на проверку'),
        ('under_review', 'На проверке'),
        ('done', 'Выполнена'),
        ('rejected', 'Отклонена'),
        ('pending', 'На согласовании'),
        ('revision', 'На пересмотрении'),
        ('send_for_approve', 'Отправлено на согласование'),
    ]
    
    TASK_TYPE_CHOICES = [
        ("regular", "Обычная"),
        ("approval", "Согласование плана"),
        ("review", "Согласование выполнения"),
        ("task_approval", "Согласование задачи"),
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
    redirected_by = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name="redirected_tasks", verbose_name="Перенаправлена от")
    
    # Согласование создания задачи
    is_according_to_plan = models.BooleanField(
        default=True,
        verbose_name="Согласно плана",
        help_text="Флаг, создана ли задача согласно плана",
    )
    
    # Связь с другими задачами (для согласования создания и проверки выполнения)
    parent_task = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="child_tasks",
        verbose_name="Связанная задача",
    )
    relation_type = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('creation_approval', 'Согласование создания'),
            ('execution_review', 'Проверка выполнения'),
        ],
        verbose_name="Тип связи",
    )
    
    # Для ознакомления
    cc = models.ManyToManyField('Employee', blank=True, related_name="cc_tasks", verbose_name="Для ознакомления")
    # 👇 Новое поле — кому направлена задача
    recipients = models.ManyToManyField('Employee', blank=True, related_name="received_tasks", verbose_name="Адресаты")
    due_date = models.DateTimeField(null=True, blank=True)
    google_drive_link = models.URLField(blank=True, null=True, verbose_name="Ссылка на Google Диск")
    attachment = models.FileField(upload_to="tasks/files/", blank=True, null=True, verbose_name="Вложение")
    review_comment = models.TextField(blank=True, null=True, verbose_name="Комментарий проверяющего")

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    # 🔥 ДОБАВЛЕНО (нужно для уведомлений)
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("task_detail", args=[self.id])
    
    # 🔥 ДОБАВЛЕНО (нужно для API и отображения срочности)
    @property
    def is_urgent(self):
        if not self.due_date:
            return False
        # Считаем срочной, если дедлайн <= чем через 3 дня и задача активна
        return (
            self.due_date.date() <= timezone.now().date() + timedelta(days=3)
            and self.status in ["new", "in_progress"]
        )
    
    # ============================================================
    # 🔥 НОВЫЕ HELPER МЕТОДЫ для работы с цепочками согласования
    # ============================================================
    
    def get_current_approver(self):
        """Получить текущего согласующего (первого из ожидающих)"""
        return self.approval_chain.filter(status='pending').order_by('order').first()
    
    def get_next_approver(self):
        """Получить следующего согласующего после текущего"""
        current = self.get_current_approver()
        if not current:
            return None
        return self.approval_chain.filter(
            order__gt=current.order,
            status='pending'
        ).order_by('order').first()
    
    def get_pending_approvers(self):
        """Получить всех ожидающих согласующих"""
        return self.approval_chain.filter(status='pending').order_by('order')
    
    def get_approval_chain_display(self):
        """Получить цепочку в виде [{id, name, status, approved_at}, ...]"""
        return [
            {
                'id': ac.approver.id,
                'name': ac.approver.full_name,
                'status': ac.status,
                'approved_at': ac.approved_at,
                'rejection_reason': ac.rejection_reason,
            }
            for ac in self.approval_chain.all()
        ]
    
    def get_current_reviewer(self):
        """Получить текущего проверяющего"""
        return self.review_chain.filter(status='pending').order_by('order').first()
    
    def get_review_chain_display(self):
        """Получить цепочку проверяющих"""
        return [
            {
                'id': rc.reviewer.id,
                'name': rc.reviewer.full_name,
                'status': rc.status,
                'reviewed_at': rc.reviewed_at,
                'review_comment': rc.review_comment,
            }
            for rc in self.review_chain.all()
        ]
    
    def get_redirect_chain_display(self):
        """Получить цепочку перенаправлений"""
        return [
            {
                'from_id': rc.from_employee.id,
                'from_name': rc.from_employee.full_name,
                'to_id': rc.to_employee.id,
                'to_name': rc.to_employee.full_name,
                'redirected_at': rc.redirected_at,
                'reason': rc.reason,
            }
            for rc in self.redirect_chain.all()
        ]
    
    def add_to_approval_chain(self, approver, order=None):
        """Добавить согласующего в цепочку"""
        if order is None:
            # Получить максимальный порядок + 1
            max_order = self.approval_chain.aggregate(
                max_order=models.Max('order')
            )['max_order'] or 0
            order = max_order + 1
        
        return self.approval_chain.create(
            approver=approver,
            order=order,
            status='pending'
        )
    
    def add_to_review_chain(self, reviewer, order=None):
        """Добавить проверяющего в цепочку"""
        if order is None:
            max_order = self.review_chain.aggregate(
                max_order=models.Max('order')
            )['max_order'] or 0
            order = max_order + 1
        
        return self.review_chain.create(
            reviewer=reviewer,
            order=order,
            status='pending'
        )
    
    def approve_by(self, employee):
        """Одобрить согласованием текущего согласующего"""
        current = self.get_current_approver()
        if not current or current.approver != employee:
            raise ValueError(f"Employee {employee} is not the current approver")
        
        current.status = 'approved'
        current.approved_at = timezone.now()
        current.save()
        
        # Если есть следующий согласующий - ждем его
        # Если нет - задача может идти дальше
        return current
    
    def reject_by(self, employee, reason=''):
        """Отклонить согласование"""
        current = self.get_current_approver()
        if not current or current.approver != employee:
            raise ValueError(f"Employee {employee} is not the current approver")
        
        current.status = 'rejected'
        current.rejection_reason = reason
        current.approved_at = timezone.now()
        current.save()
        
        # Все остальные согласования отменяются
        self.approval_chain.filter(status='pending').update(status='rejected')
        
        return current


class TaskHistory(models.Model):
    ACTION_CHOICES = [
        ("created", "Создана"),
        ("assigned", "Назначена"),
        ("taken", "Взята в работу"),
        ("sent_for_review", "Отправлена на проверку"),
        ("under_review", "На проверке"),
        ("rejected", "Отклонена"),
        ("redirected", "Перенаправлена"),
        ("return_redirect", "Возврат перенаправления"),
        ("executed", "Исполнена"),
        ("done", "Завершена"),
        ("execution_updated", "Обновлено выполнение"), # Добавлено, чтобы совпадало с views
        ("updated", "Отредактирована"), # Добавлено для редактирования задачи создателем
        ("approved", "Утверждена"), # Добавлено
        ("completed", "Завершена"), # Добавлено
        ("delegated", "Делегирована"), # Добавлено
        ("sent_for_approve", "Отправлена на согласование"),
        ("pending", "На согласовании"),
        ("revision", "На пересмотрении"),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="history")
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        name = self.employee.full_name if self.employee else "Система"
        return f"{self.get_action_display()} — {self.task.title} ({self.timestamp:%d.%m.%Y %H:%M})"


class TaskAttachment(models.Model):
    task = models.ForeignKey("Task", on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="tasks/execution_files/", blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    uploaded_by = models.ForeignKey("Employee", on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name if self.file else self.link or "Вложение"


# =========================================================
# 🔥 МОДЕЛИ, КОТОРЫЕ БЫЛИ УДАЛЕНЫ, НО НУЖНЫ ДЛЯ МОБИЛКИ
# =========================================================

class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        name = self.author.full_name if self.author else "Система"
        return f"Комментарий от {name} для задачи {self.task_id}"


class Notification(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    message = models.CharField(max_length=500)
    url = models.CharField(max_length=300, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}: {self.message[:40]}"


# =========================================================
# 🔥 НОВЫЕ МОДЕЛИ: Нормализованные цепочки согласования
# =========================================================

class TaskApprovalChain(models.Model):
    """
    Цепочка согласующих при создании задачи (замена creation_approval_chain JSON)
    """
    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Ожидание'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='approval_chain')
    approver = models.ForeignKey(Employee, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    
    status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='pending'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ('task', 'order')
        indexes = [
            models.Index(fields=['task', 'status']),
            models.Index(fields=['approver', 'status']),
        ]
    
    def __str__(self):
        return f"{self.task.title} → {self.approver.full_name} ({self.get_status_display()})"


class TaskReviewChain(models.Model):
    """
    Цепочка проверяющих при проверке выполнения (замена reviewers_chain JSON)
    """
    REVIEW_STATUS_CHOICES = [
        ('pending', 'Ожидание'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='review_chain')
    reviewer = models.ForeignKey(Employee, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    
    status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default='pending'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comment = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ('task', 'order')
        indexes = [
            models.Index(fields=['task', 'status']),
            models.Index(fields=['reviewer', 'status']),
        ]
    
    def __str__(self):
        return f"{self.task.title} → {self.reviewer.full_name} (Review: {self.get_status_display()})"


class TaskRedirectChain(models.Model):
    """
    Цепочка перенаправлений между сотрудниками (замена redirect_chain JSON)
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='redirect_chain')
    from_employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='redirected_from'
    )
    to_employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='redirected_to'
    )
    order = models.PositiveIntegerField()
    redirected_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ('task', 'order')
        indexes = [
            models.Index(fields=['from_employee', 'to_employee']),
        ]
    
    def __str__(self):
        return f"{self.task.title}: {self.from_employee.full_name} → {self.to_employee.full_name}"


class FCMDevice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="fcm_devices")
    token = models.TextField(unique=True)   # Токен устройства для Push-уведомлений
    platform = models.CharField(max_length=20, default="android")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} | {self.platform}"