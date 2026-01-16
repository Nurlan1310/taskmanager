from django.contrib import admin
from .models import (
    Employee, Department, Task, EventCard, 
    TaskHistory, CardApproverOrder, Category, TaskAttachment,
    # 🔥 Добавили твои модели
    TaskComment, Notification, FCMDevice
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "priority")
    list_editable = ("priority",)
    search_fields = ("name",)
    ordering = ("priority", "name")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("user", "position", "department", "role", "internal_phone", "delegate_to", "delegate_until")
    list_filter = ("role", "department")
    search_fields = ("user__username", "user__first_name", "user__last_name", "position", "internal_phone")
    raw_id_fields = ("user", "department")
    fieldsets = (
        ("Основная информация", {
            "fields": ("user", "department", "role", "position", "photo", "internal_phone")
        }),
        ("Замещение", {
            "fields": ("delegate_to", "delegate_until"),
            "description": "Укажите, кто и до какой даты замещает данного сотрудника."
        }),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(EventCard)
class EventCardAdmin(admin.ModelAdmin):
    list_display = ("title", "start_date", "end_date", "created_by", "progress", "responsible_department", "plan_status", "visible")
    list_filter = ("plan_status", "visible", "start_date", "categories", "responsible_department",)
    search_fields = ("title", "description")
    filter_horizontal = ("categories", "shared_departments")


# 🔹 Inline для истории задач
class TaskHistoryInline(admin.TabularInline):
    model = TaskHistory
    extra = 0
    readonly_fields = ("employee", "action", "comment", "timestamp")
    ordering = ("-timestamp",)
    can_delete = False


# 🔹 Inline для вложений (файлы/ссылки)
class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 0
    readonly_fields = ("file", "link", "uploaded_by", "uploaded_at")
    ordering = ("-uploaded_at",)
    can_delete = False


# 🔹 Inline для комментариев (чтобы видеть их внутри задачи)
class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    readonly_fields = ("author", "text", "created_at")
    ordering = ("-created_at",)
    can_delete = True


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("card", "title", "status", "created_by", "assigned_department", "assigned_employee", "deadline", "is_urgent")
    list_filter = ("status", "assigned_department", "card", "priority")
    search_fields = ("title", "description")
    raw_id_fields = ("created_by", "assigned_department", "assigned_employee")
    filter_horizontal = ("cc", "recipients")

    # Добавили комментарии в просмотр задачи
    inlines = [TaskAttachmentInline, TaskHistoryInline, TaskCommentInline]


# ==========================================
# 🔥 НОВЫЕ РАЗДЕЛЫ ДЛЯ МОБИЛКИ
# ==========================================

@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ("task", "author", "text_short", "created_at")
    search_fields = ("text", "author__user__username", "task__title")
    
    def text_short(self, obj):
        return obj.text[:50]
    text_short.short_description = "Текст"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__username", "message")


@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "token_short", "created_at")
    list_filter = ("platform",)
    search_fields = ("user__username",)

    def token_short(self, obj):
        return obj.token[:20] + "..."
    token_short.short_description = "Токен"