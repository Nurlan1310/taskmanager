from django.contrib import admin
from .models import (
    Employee, Department, Task, EventCard, 
    TaskHistory, CardApproverOrder, Category, TaskAttachment
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("user", "position", "department", "role", "delegate_to", "delegate_until")
    list_filter = ("role", "department")
    search_fields = ("user__username", "user__first_name", "user__last_name", "position",)
    raw_id_fields = ("user", "department")
    fieldsets = (
        ("Основная информация", {
            "fields": ("user", "department", "role", "position")
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
    filter_horizontal = ("categories", "shared_departments", "approvers")


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


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("card", "title", "status", "created_by", "assigned_department", "assigned_employee", "deadline")
    list_filter = ("status", "assigned_department", "card")
    search_fields = ("title", "description")
    raw_id_fields = ("created_by", "assigned_department", "assigned_employee")
    filter_horizontal = ("cc", "recipients")

    inlines = [TaskAttachmentInline, TaskHistoryInline]
