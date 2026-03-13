from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import (
    Employee,
    Department,
    Task,
    TaskHistory,
    KPIReport,
    KPIResult,
    KPIRoleConfig,
)

# Единая формула KPI: базовые веса критериев (сумма ≈ 100).
# Могут быть переопределены в админке через KPIRoleConfig.positive_weights по ролям.
WEIGHT_TIMELINESS = 30   # Своевременность
WEIGHT_COMPLETION = 25   # Выполнение
WEIGHT_WORKLOAD = 20     # Нагрузка
WEIGHT_RELIABILITY = 15  # Надёжность / качество
WEIGHT_MANAGEMENT = 10   # Управление / дисциплина

DEFAULT_COMPONENT_WEIGHTS = {
    "timeliness": WEIGHT_TIMELINESS,
    "completion": WEIGHT_COMPLETION,
    "workload": WEIGHT_WORKLOAD,
    "reliability": WEIGHT_RELIABILITY,
    "management": WEIGHT_MANAGEMENT,
}


def _get_component_weights_for_role(role: str) -> dict:
    """
    Возвращает веса блоков KPI для указанной роли.
    Берёт positive_weights из KPIRoleConfig (formula_version='v2'),
    при отсутствии записи или отдельных ключей использует дефолты.
    """
    weights = DEFAULT_COMPONENT_WEIGHTS.copy()
    cfg = KPIRoleConfig.objects.filter(role=role, formula_version="v2").first()
    if cfg and cfg.positive_weights:
        for key in weights.keys():
            if key in cfg.positive_weights:
                try:
                    weights[key] = float(cfg.positive_weights[key])
                except (TypeError, ValueError):
                    # игнорируем некорректные значения, остаются дефолты
                    pass
    return weights


@dataclass
class KpiComponentScore:
    value: float
    max_value: float

    def normalized(self) -> float:
        if self.max_value <= 0:
            return 0.0
        return max(0.0, min(1.0, self.value / self.max_value))


@dataclass
class KpiBreakdown:
    timeliness: float = 0.0
    completion: float = 0.0
    workload: float = 0.0
    reliability: float = 0.0
    management: float = 0.0

    def total(self) -> float:
        return (
            self.timeliness
            + self.completion
            + self.workload
            + self.reliability
            + self.management
        )


def _get_month_bounds(year: int, month: int) -> Tuple[timezone.datetime, timezone.datetime]:
    """Вернуть (начало месяца, конец месяца) в aware-формате."""
    from datetime import datetime, timedelta

    tz = timezone.get_current_timezone()
    start = datetime(year=year, month=month, day=1)
    if month == 12:
        next_month = datetime(year=year + 1, month=1, day=1)
    else:
        next_month = datetime(year=year, month=month + 1, day=1)
    end = next_month - timedelta(microseconds=1)
    return timezone.make_aware(start, tz), timezone.make_aware(end, tz)


def _get_effective_completed_at(task: Task) -> timezone.datetime | None:
    """
    Унифицированный способ получить дату завершения задачи:
    1) Task.completed_at, если заполнен;
    2) последний TaskHistory с действием done/completed/approved/executed.
    """
    if task.completed_at:
        return task.completed_at

    completion_actions = ["done", "completed", "approved", "executed"]
    history = (
        TaskHistory.objects.filter(task=task, action__in=completion_actions)
        .order_by("-timestamp")
        .first()
    )
    return history.timestamp if history else None


def _collect_employee_tasks_for_month(
    employee: Employee, start: timezone.datetime, end: timezone.datetime
) -> Dict[str, List[Task]]:
    """
    Собирает выборки задач для KPI сотрудника за месяц.

    Основной фокус — задачи, где сотрудник выступает исполнителем (assigned_employee).
    """
    # Обычные исполнительские задачи
    base_qs = Task.objects.filter(assigned_employee=employee).select_related(
        "assigned_employee", "assigned_department", "card"
    )

    regular_tasks = base_qs.filter(task_type="regular")

    # Задачи, которые считаем "завершенными в месяце"
    regular_done_in_month: List[Task] = []
    for task in regular_tasks.filter(status="done"):
        completed_at = _get_effective_completed_at(task)
        if completed_at and start <= completed_at <= end:
            regular_done_in_month.append(task)

    # Задачи с дедлайном в этом месяце
    regular_with_due = regular_tasks.filter(due_date__isnull=False, due_date__gte=start, due_date__lte=end)

    # Задачи, которые на конец месяца просрочены (дедлайн < конец месяца и не завершены до конца месяца)
    overdue_at_month_end: List[Task] = []
    for task in regular_tasks.filter(due_date__isnull=False):
        if task.due_date and task.due_date <= end:
            completed_at = _get_effective_completed_at(task)
            if not completed_at or completed_at > end:
                overdue_at_month_end.append(task)

    # Служебные задачи для управленческой активности
    approval_tasks = base_qs.filter(task_type__in=["approval", "review", "task_approval"])

    return {
        "regular_all": list(regular_tasks),
        "regular_done_in_month": regular_done_in_month,
        "regular_with_due_in_month": list(regular_with_due),
        "regular_overdue_at_month_end": overdue_at_month_end,
        "approval_like": list(approval_tasks),
    }


def _calc_staff_senior_kpi(
    employee: Employee,
    month_tasks: Dict[str, List[Task]],
    start: timezone.datetime,
    end: timezone.datetime,
) -> Tuple[float, Dict, Dict]:
    """
    KPI для исполнителей (staff / senior).
    Возвращает (score, metrics, breakdown).
    """
    role = employee.role
    component_weights = _get_component_weights_for_role(role)

    regular_all = month_tasks["regular_all"]
    regular_done_in_month = month_tasks["regular_done_in_month"]
    regular_with_due = month_tasks["regular_with_due_in_month"]
    regular_overdue_at_month_end = month_tasks["regular_overdue_at_month_end"]

    total_regular = len(regular_all)
    done_in_month = len(regular_done_in_month)
    with_due = len(regular_with_due)
    overdue_end = len(regular_overdue_at_month_end)

    # --- Timeliness (0..WEIGHT_TIMELINESS) ---
    on_time = 0
    urgent_on_time = 0
    urgent_total = 0

    for task in regular_done_in_month:
        if not task.due_date:
            continue
        completed_at = _get_effective_completed_at(task)
        if not completed_at:
            continue
        if completed_at <= task.due_date:
            on_time += 1
            if task.priority == "urgent":
                urgent_on_time += 1
        if task.priority == "urgent":
            urgent_total += 1

    timeliness_base = KpiComponentScore(
        value=on_time,
        max_value=with_due if with_due > 0 else 1,
    ).normalized()

    if with_due > 0:
        overdue_ratio = min(1.0, overdue_end / with_due)
    else:
        overdue_ratio = 0.0

    timeliness_score = component_weights["timeliness"] * timeliness_base * (1.0 - 0.7 * overdue_ratio)
    if urgent_total > 0 and urgent_on_time / urgent_total < 0.5:
        timeliness_score *= 0.8

    # --- Completion (0..WEIGHT_COMPLETION) ---
    taken_actions = (
        TaskHistory.objects.filter(
            task__in=regular_all,
            action="taken",
        )
        .values_list("task_id", flat=True)
        .distinct()
    )
    taken_count = len(taken_actions)

    rejected_count = (
        TaskHistory.objects.filter(
            task__in=regular_all,
            action__in=["rejected", "revision"],
        )
        .values("task_id")
        .distinct()
        .count()
    )

    if taken_count > 0:
        completion_ratio = done_in_month / taken_count
    else:
        completion_ratio = 1.0  # если задач не брали в работу, не штрафуем

    completion_score = component_weights["completion"] * completion_ratio
    if taken_count > 0:
        completion_score *= max(0.0, 1.0 - 0.5 * (rejected_count / taken_count))

    # --- Workload (0..WEIGHT_WORKLOAD) ---
    M = 50
    workload_ratio = min(1.0, total_regular / M) if M > 0 else 0.0
    workload_score = component_weights["workload"] * workload_ratio

    # --- Reliability (0..WEIGHT_RELIABILITY) ---
    # Берём сигнал от наличия результатов исполнения (вложения/ссылки)
    tasks_with_attachments = (
        Task.objects.filter(id__in=[t.id for t in regular_done_in_month], attachments__isnull=False)
        .distinct()
        .count()
    )
    if done_in_month > 0:
        attachments_ratio = tasks_with_attachments / done_in_month
    else:
        attachments_ratio = 0.0
    reliability_score = component_weights["reliability"] * attachments_ratio

    breakdown = KpiBreakdown(
        timeliness=round(timeliness_score, 2),
        completion=round(completion_score, 2),
        workload=round(workload_score, 2),
        reliability=round(reliability_score, 2),
        management=0.0,
    )

    metrics = {
        "role_group": "staff_senior",
        "total_regular": total_regular,
        "done_in_month": done_in_month,
        "with_due": with_due,
        "overdue_at_month_end": overdue_end,
        "urgent_total": urgent_total,
        "urgent_on_time": urgent_on_time,
        "taken_count": taken_count,
        "rejected_or_revision_tasks": rejected_count,
        "tasks_with_attachments": tasks_with_attachments,
    }

    flags = {}
    if total_regular < 5:
        flags["low_sample"] = True

    return round(breakdown.total(), 2), metrics, {**asdict(breakdown), "flags": flags}


def _calc_head_kpi(
    employee: Employee,
    month_tasks: Dict[str, List[Task]],
    start: timezone.datetime,
    end: timezone.datetime,
) -> Tuple[float, Dict, Dict]:
    """
    Упрощённый KPI для руководителя отдела.
    Основная идея: агрегированное качество задач отдела + немного личного KPI.
    """
    role = employee.role
    component_weights = _get_component_weights_for_role(role)

    # Личный KPI как у исполнителя (для простоты) с меньшим весом.
    personal_score, personal_metrics, personal_breakdown = _calc_staff_senior_kpi(
        employee, month_tasks, start, end
    )

    # Задачи отдела: все задачи, где assigned_department = отдел руководителя
    dept = employee.department
    dept_metrics = {}
    dept_score_timeliness = 0.0
    dept_score_completion = 0.0

    if dept:
        dept_tasks = (
            Task.objects.filter(
                Q(assigned_department=dept) | Q(assigned_employee__department=dept),
                task_type="regular",
            )
            .select_related("assigned_employee", "assigned_department")
            .distinct()
        )

        total_dept = dept_tasks.count()
        done_dept = 0
        overdue_dept = 0
        with_due_dept = 0

        for task in dept_tasks:
            completed_at = _get_effective_completed_at(task)
            if completed_at and start <= completed_at <= end and task.status == "done":
                done_dept += 1
            if task.due_date:
                with_due_dept += 1
                if task.due_date <= end:
                    if not completed_at or completed_at > end:
                        overdue_dept += 1

        dept_metrics = {
            "dept_id": dept.id,
            "dept_name": dept.name,
            "dept_total_tasks": total_dept,
            "dept_done_tasks": done_dept,
            "dept_with_due": with_due_dept,
            "dept_overdue_at_month_end": overdue_dept,
        }

        if with_due_dept > 0:
            dept_timeliness_ratio = max(0.0, (with_due_dept - overdue_dept) / with_due_dept)
        else:
            dept_timeliness_ratio = 1.0

        if total_dept > 0:
            dept_completion_ratio = done_dept / total_dept
        else:
            dept_completion_ratio = 1.0

        dept_score_timeliness = component_weights["timeliness"] * dept_timeliness_ratio
        dept_score_completion = component_weights["completion"] * dept_completion_ratio

    mgmt_score = 0.0
    if dept:
        hanging_tasks = Task.objects.filter(
            Q(assigned_department=dept) | Q(assigned_employee__department=dept),
            status__in=["new", "pending", "under_review"],
            created_at__lte=end,
        ).count()
        if hanging_tasks == 0:
            mgmt_score = component_weights["management"]
        else:
            mgmt_score = max(0.0, component_weights["management"] - min(component_weights["management"], hanging_tasks))

    # Нагрузка: доля личного KPI в пределах веса workload
    personal_workload = min(1.0, personal_score / 100.0) * component_weights["workload"] if personal_score else 0.0

    breakdown = KpiBreakdown(
        timeliness=round(dept_score_timeliness, 2),
        completion=round(dept_score_completion, 2),
        workload=round(personal_workload, 2),
        reliability=0.0,
        management=round(mgmt_score, 2),
    )

    metrics = {
        "role_group": "head",
        "personal": personal_metrics,
        "department": dept_metrics,
    }
    flags = {}
    return round(breakdown.total(), 2), metrics, {**asdict(breakdown), "flags": flags}


def _calc_director_deputy_kpi(
    employee: Employee,
    month_tasks: Dict[str, List[Task]],
    start: timezone.datetime,
    end: timezone.datetime,
) -> Tuple[float, Dict, Dict]:
    """
    Упрощённый KPI для директора и замов.
    Фокус: скорость согласований/проверок и отсутствие зависших служебных задач.
    """
    role = employee.role
    component_weights = _get_component_weights_for_role(role)

    approval_tasks = month_tasks["approval_like"]

    total_approval = len(approval_tasks)
    decided_count = 0
    slow_decisions = 0
    hanging = 0

    from datetime import timedelta

    for task in approval_tasks:
        # дата назначения — первая запись taken для этой задачи
        taken = (
            TaskHistory.objects.filter(task=task, action="taken")
            .order_by("timestamp")
            .first()
        )
        assigned_at = taken.timestamp if taken else task.created_at
        completed_at = _get_effective_completed_at(task)

        if completed_at:
            decided_count += 1
            delta = completed_at - assigned_at
            if delta > timedelta(days=3):
                slow_decisions += 1
        else:
            if task.created_at <= end:
                hanging += 1

    speed_score = 0.0
    backlog_score = 0.0

    if total_approval > 0:
        decided_ratio = decided_count / total_approval
        speed_score = component_weights["timeliness"] * decided_ratio
        if decided_count > 0:
            slow_ratio = slow_decisions / decided_count
            speed_score *= max(0.0, 1.0 - 0.5 * slow_ratio)

        backlog_ratio = min(1.0, hanging / total_approval)
        backlog_score = component_weights["management"] * (1.0 - backlog_ratio)

    personal_score, personal_metrics, _ = _calc_staff_senior_kpi(
        employee, month_tasks, start, end
    )
    personal_workload = min(1.0, personal_score / 100.0) * component_weights["workload"] if personal_score else 0.0

    breakdown = KpiBreakdown(
        timeliness=round(speed_score, 2),
        completion=0.0,
        workload=round(personal_workload, 2),
        reliability=0.0,
        management=round(backlog_score, 2),
    )

    metrics = {
        "role_group": "director_deputy",
        "total_approval_like": total_approval,
        "decided_count": decided_count,
        "slow_decisions": slow_decisions,
        "hanging": hanging,
        "personal": personal_metrics,
    }
    flags = {}
    return round(breakdown.total(), 2), metrics, {**asdict(breakdown), "flags": flags}


def calculate_employee_kpi(
    employee: Employee, year: int, month: int
) -> Tuple[float, Dict, Dict]:
    """
    Расчёт KPI по одному сотруднику за месяц.
    Единая формула: своевременность 30%, выполнение 25%, нагрузка 20%, надёжность 15%, управление 10%.
    """
    start, end = _get_month_bounds(year, month)
    month_tasks = _collect_employee_tasks_for_month(employee, start, end)
    role = employee.role

    if role in ("staff", "senior"):
        return _calc_staff_senior_kpi(employee, month_tasks, start, end)
    if role == "head":
        return _calc_head_kpi(employee, month_tasks, start, end)
    if role in ("director", "deputy"):
        return _calc_director_deputy_kpi(employee, month_tasks, start, end)
    return _calc_staff_senior_kpi(employee, month_tasks, start, end)


@transaction.atomic
def generate_kpi_report(year: int, month: int, user: User) -> KPIReport:
    """
    Сформировать предварительную оценку KPI за месяц (черновик).
    Админ видит превью и подтверждает публикацию отдельным действием.
    """
    report, created = KPIReport.objects.get_or_create(
        year=year,
        month=month,
        defaults={"generated_by": user, "status": "draft"},
    )

    if not created:
        report.generated_by = user
        report.generated_at = timezone.now()
        report.status = "draft"
        report.message = ""
        report.save(update_fields=["generated_by", "generated_at", "status", "message"])
        KPIResult.objects.filter(report=report).delete()

    employees_with_tasks = (
        Employee.objects.filter(tasks__isnull=False)
        .select_related("department", "user")
        .distinct()
    )

    for employee in employees_with_tasks:
        score, metrics, breakdown = calculate_employee_kpi(employee, year, month)
        KPIResult.objects.create(
            report=report,
            employee=employee,
            department=employee.department,
            role_snapshot=employee.role,
            score=score,
            metrics_json=metrics,
            breakdown_json=breakdown,
            flags_json=breakdown.get("flags") or {},
        )

    return report


def publish_kpi_report(report: KPIReport) -> None:
    """Опубликовать отчёт KPI (подтверждение админом)."""
    if report.status != "draft":
        raise ValueError("Можно опубликовать только черновик")
    report.status = "published"
    report.save(update_fields=["status"])

