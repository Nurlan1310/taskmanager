# assistant/services/analytics.py

from datetime import timedelta, datetime, date
from django.utils import timezone
from django.db.models import Count, Q, Min
from tasks.models import Task

PERFORMER_ACTIVE_STATUSES = ["new", "in_progress"]

def _get_employee(user):
    return getattr(user, "employee", None)

def _base_queryset_for_user(user):
    employee = _get_employee(user)
    if not employee:
        return Task.objects.none()
    qs = Task.objects.all()
    if employee.role in ["director", "deputy"]:
        return qs.distinct()
    if employee.role == "head" and employee.department_id:
        return qs.filter(
            Q(assigned_department=employee.department) |
            Q(assigned_employee=employee) |
            Q(created_by=employee) |
            Q(recipients=employee) |
            Q(cc=employee)
        ).distinct()
    return qs.filter(
        Q(assigned_employee=employee) | Q(recipients=employee) |
        Q(cc=employee) | Q(created_by=employee)
    ).distinct()

def _urgent_filter(today):
    return Q(due_date__isnull=False, due_date__lte=today + timedelta(days=3), status__in=PERFORMER_ACTIVE_STATUSES)

def _overdue_filter(today):
    return Q(due_date__isnull=False, due_date__lt=today, status__in=PERFORMER_ACTIVE_STATUSES)

def analytics_for_user(user):
    today = timezone.now().date()
    qs = _base_queryset_for_user(user)

    # 1. Сбор списков с ПРИНУДИТЕЛЬНОЙ конвертацией дат в строки (иначе будет ошибка 500)
    upcoming_raw = qs.filter(due_date__gt=today + timedelta(days=3), status__in=PERFORMER_ACTIVE_STATUSES).order_by("due_date")[:15]
    upcoming_tasks = [
        {"title": t.title, "due_date": str(t.due_date)} for t in upcoming_raw
    ]

    recent_raw = qs.filter(status="done").order_by("-completed_at")[:10]
    recent_completed = [
        {"title": t.title, "completed_at": str(t.completed_at.date()) if t.completed_at else "Недавно"} for t in recent_raw
    ]

    # 2. Ближайший дедлайн
    next_due = qs.filter(due_date__isnull=False, status__in=PERFORMER_ACTIVE_STATUSES).aggregate(m=Min("due_date"))['m']

    return {
        "total_tasks": qs.count(),
        "urgent_tasks": qs.filter(_urgent_filter(today)).count(),
        "overdue_tasks": qs.filter(_overdue_filter(today)).count(),
        "by_status": list(qs.values("status").annotate(count=Count("id"))),
        "next_due_date": str(next_due) if next_due else None,
        "upcoming_tasks": upcoming_tasks,
        "recent_completed": recent_completed,
    }

def workload_by_employee(user):
    employee = _get_employee(user)
    if not employee or employee.role not in ["director", "deputy", "head"]:
        return []
    
    qs = Task.objects.filter(assigned_employee__isnull=False)
    if employee.role == "head":
        qs = qs.filter(assigned_employee__department=employee.department)
    
    today = timezone.now().date()
    
    # Считаем нагрузку
    data = qs.values(
        "assigned_employee__user__first_name",
        "assigned_employee__user__last_name",
        "assigned_employee__department__name",
    ).annotate(
        total=Count("id"),
        urgent=Count("id", filter=_urgent_filter(today)),
        overdue=Count("id", filter=_overdue_filter(today)),
    ).order_by("-total")

    return list(data)

def insights(stats, workload):
    lines = []
    
    # ПРОВЕРКА: Если список workload пуст, не пытаемся брать [0] элемент (это вызывает 500)
    if workload and len(workload) > 0:
        top = workload[0]
        fn = str(top.get("assigned_employee__user__first_name") or "").strip()
        ln = str(top.get("assigned_employee__user__last_name") or "").strip()
        who = f"{fn} {ln}".strip() or "Сотрудник"
        lines.append(f"Наибольшая нагрузка: {who} (задач: {top['total']}).")

    overdue = stats.get("overdue_tasks", 0)
    if overdue > 0:
        lines.append(f"Внимание: обнаружено {overdue} просроченных задач.")
        
    return "\n".join(lines) if lines else "Критичных рисков не обнаружено."