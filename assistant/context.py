# assistant/context.py

from datetime import timedelta
from django.utils import timezone
from django.db.models import Q

from tasks.models import Task
from employees.models import Employee


ACTIVE_STATUSES = ["new", "in_progress", "sent_for_review", "under_review"]


# =====================================================
# БАЗОВАЯ ВЫБОРКА — 1:1 КАК В MyTasksApi
# =====================================================
def _base_queryset_for_user(user):
    employee = getattr(user, "employee", None)
    if not employee:
        return Task.objects.none()

    qs = Task.objects.all()

    # Директор / зам — всё
    if employee.role in ["director", "deputy"]:
        return qs.distinct()

    # Руководитель отдела
    if employee.role == "head" and employee.department_id:
        return qs.filter(
            Q(assigned_department=employee.department) |
            Q(assigned_employee=employee) |
            Q(created_by=employee) |
            Q(recipients=employee) |
            Q(cc=employee)
        ).distinct()

    # Обычный сотрудник
    return qs.filter(
        Q(assigned_employee=employee) |
        Q(recipients=employee) |
        Q(cc=employee) |
        Q(created_by=employee)
    ).distinct()


# =====================================================
# ФИЛЬТРЫ (ВМЕСТО is_urgent PROPERTY)
# =====================================================
def _urgent_filter(today):
    return Q(
        due_date__isnull=False,
        due_date__lte=today + timedelta(days=3),
        status__in=["new", "in_progress"],
    )


def _overdue_filter(today):
    return Q(
        due_date__isnull=False,
        due_date__lt=today,
        status__in=ACTIVE_STATUSES,
    )


# =====================================================
# ОСНОВНОЙ CONTEXT ДЛЯ ASSISTANT
# =====================================================
def build_context(user):
    today = timezone.now().date()
    qs = _base_queryset_for_user(user)

    total = qs.count()
    active = qs.filter(status__in=ACTIVE_STATUSES).count()
    urgent = qs.filter(_urgent_filter(today)).count()
    overdue = qs.filter(_overdue_filter(today)).count()

    next_due = (
        qs.filter(
            due_date__isnull=False,
            status__in=ACTIVE_STATUSES
        )
        .order_by("due_date")
        .values_list("due_date", flat=True)
        .first()
    )

    context = {
        "my_tasks": {
            "total": total,
            "active": active,
            "urgent": urgent,
            "overdue": overdue,
            "next_due_date": str(next_due) if next_due else None,
        }
    }

    return context