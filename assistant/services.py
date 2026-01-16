# assistant/services.py

from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q, Min

from tasks.models import Task
from employees.models import Employee


OPEN_STATUSES = ["new", "in_progress", "sent_for_review", "under_review"]


# =====================================================
# 👤 ЭФФЕКТИВНЫЙ СОТРУДНИК (с учётом замещения)
# =====================================================
def _get_effective_employee(user):
    employee = getattr(user, "employee", None)
    if not employee:
        return None

    try:
        return employee.get_effective_employee()
    except Exception:
        return employee


# =====================================================
# 👀 ЗАДАЧИ, КОТОРЫЕ ПОЛЬЗОВАТЕЛЬ РЕАЛЬНО ВИДИТ (1-в-1 с web)
# =====================================================
def _visible_tasks_for_employee(employee: Employee):
    if not employee:
        return Task.objects.none()

    # Руководство — всё
    if employee.role in ["director", "deputy"]:
        return Task.objects.all()

    # Руководитель отдела — свой отдел + личные
    if employee.role == "head":
        return Task.objects.filter(
            Q(assigned_employee=employee)
            | Q(assigned_department=employee.department)
            | Q(created_by=employee)
            | Q(cc=employee)
            | Q(recipients=employee)
        ).distinct()

    # Обычный сотрудник — ТОЛЬКО личные задачи
    return Task.objects.filter(
        Q(assigned_employee=employee)
        | Q(created_by=employee)
        | Q(cc=employee)
        | Q(recipients=employee)
    ).distinct()


# =====================================================
# 📊 АНАЛИТИКА ДЛЯ ПОЛЬЗОВАТЕЛЯ (WEB == MOBILE == ASSISTANT)
# =====================================================
def analytics_for_user(user):
    today = timezone.now().date()
    eff = _get_effective_employee(user)

    qs = _visible_tasks_for_employee(eff)

    urgent_qs = qs.filter(
        due_date__isnull=False,
        due_date__lte=today + timedelta(days=3),
        status__in=["new", "in_progress"],
    )

    overdue_qs = qs.filter(
        due_date__isnull=False,
        due_date__lt=today,
        status__in=["new", "in_progress"],
    )

    next_due = (
        qs.filter(due_date__isnull=False)
        .exclude(status__in=["done", "rejected"])
        .aggregate(next_due_date=Min("due_date"))
        .get("next_due_date")
    )

    by_status = list(
        qs.values("status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return {
        "scope": {
            "employee_id": eff.id if eff else None,
            "role": eff.role if eff else None,
            "department": eff.department.name if eff and eff.department else None,
        },
        "total_tasks": qs.count(),
        "urgent_tasks": urgent_qs.count(),
        "overdue_tasks": overdue_qs.count(),
        "next_due_date": str(next_due) if next_due else None,
        "by_status": by_status,
    }


# =====================================================
# 🏢 НАГРУЗКА ПО СОТРУДНИКАМ (ТОЛЬКО ДЛЯ РУКОВОДСТВА)
# =====================================================
def workload_by_employee(user):
    employee = getattr(user, "employee", None)
    if not employee:
        return []

    if employee.role not in ["director", "deputy", "head"]:
        return []

    qs = Task.objects.filter(
        assigned_employee__isnull=False
    ).select_related(
        "assigned_employee__user",
        "assigned_employee__department"
    )

    if employee.role == "head":
        qs = qs.filter(
            assigned_employee__department=employee.department
        )

    today = timezone.now().date()

    return list(
        qs.values(
            "assigned_employee__id",
            "assigned_employee__user__first_name",
            "assigned_employee__user__last_name",
            "assigned_employee__department__name",
        )
        .annotate(
            total=Count("id"),
            urgent=Count(
                "id",
                filter=Q(due_date__isnull=False,
                    due_date__lte=today + timedelta(days=3),
                    status__in=["new", "in_progress"],
                ),
            ),
            overdue=Count(
                "id",
                filter=Q(
                    due_date__isnull=False,
                    due_date__lt=today,
                    status__in=["new", "in_progress"],
                ),
            ),
        )
        .order_by("-total")
    )


# =====================================================
# 🧠 УПРАВЛЕНЧЕСКИЕ ВЫВОДЫ (СТРОГО ПО ДАННЫМ)
# =====================================================
def insights(stats, workload):
    lines = []

    if workload:
        busiest = workload[0]
        fn = busiest.get("assigned_employee__user__first_name", "") or ""
        ln = busiest.get("assigned_employee__user__last_name", "") or ""
        dep = busiest.get("assigned_employee__department__name")

        who = (fn + " " + ln).strip() or "Сотрудник"
        if dep:
            who += f" ({dep})"

        lines.append(
            f"Наибольшая нагрузка: {who} — "
            f"всего {busiest['total']}, "
            f"срочных {busiest['urgent']}, "
            f"просроченных {busiest['overdue']}."
        )

    if stats["overdue_tasks"] > 0:
        lines.append(
            f"Просроченных задач: {stats['overdue_tasks']}."
        )

    if stats["urgent_tasks"] > 0:
        lines.append(
            f"Срочных задач (≤3 дней): {stats['urgent_tasks']}."
        )

    if stats.get("next_due_date"):
        lines.append(
            f"Ближайший дедлайн: {stats['next_due_date']}."
        )

    return (
        "\n".join(lines)
        if lines
        else "Критичных рисков по текущим данным не обнаружено."
    )