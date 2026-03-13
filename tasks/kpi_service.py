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
    regular_all = month_tasks["regular_all"]
    regular_done_in_month = month_tasks["regular_done_in_month"]
    regular_with_due = month_tasks["regular_with_due_in_month"]
    regular_overdue_at_month_end = month_tasks["regular_overdue_at_month_end"]

    total_regular = len(regular_all)
    done_in_month = len(regular_done_in_month)
    with_due = len(regular_with_due)
    overdue_end = len(regular_overdue_at_month_end)

    # --- Timeliness (0..50) ---
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

    # Штраф за хвосты на конец месяца
    if with_due > 0:
        overdue_ratio = min(1.0, overdue_end / with_due)
    else:
        overdue_ratio = 0.0

    timeliness_score = 50.0 * timeliness_base * (1.0 - 0.7 * overdue_ratio)

    # Усиленный штраф за срочные, если почти все срочные просрочены
    if urgent_total > 0 and urgent_on_time / urgent_total < 0.5:
        timeliness_score *= 0.8

    # --- Completion (0..25) ---
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

    completion_score = 25.0 * completion_ratio
    if taken_count > 0:
        completion_score *= max(0.0, 1.0 - 0.5 * (rejected_count / taken_count))

    # --- Workload (0..15) ---
    # На первом шаге просто нормализуем количество задач к разумному диапазону [0..M],
    # позже можно заменить на нормализацию к медиане по отделу.
    M = 30  # условная "нормальная" месячная нагрузка
    workload_ratio = min(1.0, total_regular / M) if M > 0 else 0.0
    workload_score = 15.0 * workload_ratio

    # --- Reliability (0..10) ---
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
    reliability_score = 10.0 * attachments_ratio

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

        dept_score_timeliness = 35.0 * dept_timeliness_ratio
        dept_score_completion = 25.0 * dept_completion_ratio

    # Управленческая дисциплина (простая эвристика: отсутствие большого хвоста зависших задач)
    mgmt_score = 0.0
    if dept:
        hanging_tasks = Task.objects.filter(
            Q(assigned_department=dept) | Q(assigned_employee__department=dept),
            status__in=["new", "pending", "under_review"],
            created_at__lte=end,
        ).count()
        if hanging_tasks == 0:
            mgmt_score = 20.0
        else:
            mgmt_score = max(0.0, 20.0 - min(20.0, hanging_tasks))

    breakdown = KpiBreakdown(
        timeliness=round(dept_score_timeliness, 2),
        completion=round(dept_score_completion, 2),
        workload=round(personal_score * 0.2, 2),  # личный KPI даёт до 20 баллов
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
        speed_score = 40.0 * decided_ratio
        if decided_count > 0:
            slow_ratio = slow_decisions / decided_count
            speed_score *= max(0.0, 1.0 - 0.5 * slow_ratio)

        backlog_ratio = min(1.0, hanging / total_approval)
        backlog_score = 20.0 * (1.0 - backlog_ratio)

    # Личная исполнительская дисциплина по обычным задачам — как у staff/senior, но с малым весом
    personal_score, personal_metrics, _ = _calc_staff_senior_kpi(
        employee, month_tasks, start, end
    )

    breakdown = KpiBreakdown(
        timeliness=round(speed_score, 2),
        completion=0.0,
        workload=round(personal_score * 0.1, 2),  # до 10 баллов от личного исполнения
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


def _calculate_employee_kpi_v1(
    employee: Employee, year: int, month: int
) -> Tuple[float, Dict, Dict]:
    """
    Центральная точка расчета KPI по одному сотруднику за месяц.
    Возвращает (итоговый_балл, metrics_json, breakdown_json).
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

    # Fallback: считаем как у исполнителя
    return _calc_staff_senior_kpi(employee, month_tasks, start, end)


def _get_role_config(role: str, formula_version: str) -> KPIRoleConfig | None:
    """
    Вернуть конфигурацию KPI для роли и версии формулы, если она есть.
    При отсутствии — None, тогда используются дефолтные параметры в коде.
    """
    try:
        return KPIRoleConfig.objects.get(role=role, formula_version=formula_version)
    except KPIRoleConfig.DoesNotExist:
        return None


def _compute_penalty_factor_for_staff_senior(metrics: Dict, role_cfg: KPIRoleConfig | None) -> float:
    """
    Рассчитать коэффициент штрафов для исполнителей (staff/senior).

    Логика:
    - штрафуют:
      * доля просроченных задач на конец месяца;
      * доля задач с reject/revision среди взятых;
      * доля просроченных срочных задач;
    - суммарный штраф ограничен так, чтобы коэффициент не опускался ниже penalty_min_factor.
    """
    with_due = max(1, metrics.get("with_due") or 0)
    overdue = metrics.get("overdue_at_month_end") or 0
    taken_count = max(1, metrics.get("taken_count") or 0)
    rejected_count = metrics.get("rejected_or_revision_tasks") or 0
    urgent_total = metrics.get("urgent_total") or 0
    urgent_on_time = metrics.get("urgent_on_time") or 0

    overdue_ratio = min(1.0, overdue / with_due) if with_due > 0 else 0.0
    rejected_ratio = min(1.0, rejected_count / taken_count) if taken_count > 0 else 0.0
    urgent_miss_ratio = 0.0
    if urgent_total > 0:
        urgent_miss_ratio = 1.0 - min(1.0, urgent_on_time / urgent_total)

    # Дефолтные веса, если в конфиге не задано иное
    weights = {
        "overdue_ratio": 0.4,
        "rejected_ratio": 0.3,
        "urgent_miss_ratio": 0.3,
    }
    if role_cfg and role_cfg.penalty_weights:
        weights.update(role_cfg.penalty_weights)

    penalty = (
        weights.get("overdue_ratio", 0.4) * overdue_ratio
        + weights.get("rejected_ratio", 0.3) * rejected_ratio
        + weights.get("urgent_miss_ratio", 0.3) * urgent_miss_ratio
    )

    # Суммарный штраф ограничиваем максимумом в 1.0 (100%), а затем минимальным коэффициентом
    penalty = max(0.0, min(1.0, penalty))

    min_factor = float(role_cfg.penalty_min_factor) if role_cfg else 0.60
    min_factor = max(0.0, min(1.0, min_factor))

    factor = 1.0 - penalty
    if factor < min_factor:
        factor = min_factor
    return factor


def _compute_penalty_factor_for_head(metrics: Dict, role_cfg: KPIRoleConfig | None) -> float:
    """
    Штрафы для руководителя отдела: доля просроченных задач отдела.
    """
    with_due = max(1, metrics.get("department", {}).get("dept_with_due") or 0)
    overdue = metrics.get("department", {}).get("dept_overdue_at_month_end") or 0
    overdue_ratio = min(1.0, overdue / with_due) if with_due > 0 else 0.0

    penalty = overdue_ratio  # базово: до 100% штраф при полном хвосте
    penalty = max(0.0, min(1.0, penalty))

    min_factor = float(role_cfg.penalty_min_factor) if role_cfg else 0.60
    min_factor = max(0.0, min(1.0, min_factor))

    factor = 1.0 - penalty
    if factor < min_factor:
        factor = min_factor
    return factor


def _compute_penalty_factor_for_director_deputy(metrics: Dict, role_cfg: KPIRoleConfig | None) -> float:
    """
    Штрафы для директора/заместителя: доля висящих служебных задач и доля медленных решений.
    """
    total_approval = max(1, metrics.get("total_approval_like") or 0)
    decided_count = metrics.get("decided_count") or 0
    slow_decisions = metrics.get("slow_decisions") or 0
    hanging = metrics.get("hanging") or 0

    backlog_ratio = min(1.0, hanging / total_approval)
    slow_ratio = min(1.0, slow_decisions / max(1, decided_count)) if decided_count > 0 else 0.0

    penalty = 0.6 * backlog_ratio + 0.4 * slow_ratio
    penalty = max(0.0, min(1.0, penalty))

    min_factor = float(role_cfg.penalty_min_factor) if role_cfg else 0.60
    min_factor = max(0.0, min(1.0, min_factor))

    factor = 1.0 - penalty
    if factor < min_factor:
        factor = min_factor
    return factor


def _compute_penalty_factor(role: str, metrics: Dict, role_cfg: KPIRoleConfig | None) -> float:
    """
    Унифицированный вход для расчёта коэффициента штрафов по роли.
    """
    if role in ("staff", "senior"):
        return _compute_penalty_factor_for_staff_senior(metrics, role_cfg)
    if role == "head":
        return _compute_penalty_factor_for_head(metrics, role_cfg)
    if role in ("director", "deputy"):
        return _compute_penalty_factor_for_director_deputy(metrics, role_cfg)

    # Fallback — как у исполнителей
    return _compute_penalty_factor_for_staff_senior(metrics, role_cfg)


def calculate_employee_kpi(
    employee: Employee,
    year: int,
    month: int,
    formula_version: str = "v1",
) -> Tuple[float, Dict, Dict]:
    """
    Центральная точка расчета KPI по одному сотруднику за месяц (v1/v2).

    formula_version:
    - v1 — использовать историческую формулу и структуру breakdown;
    - v2 — использовать двухэтажную схему: positive_cap * penalty_factor.
    """
    base_score, metrics, breakdown = _calculate_employee_kpi_v1(employee, year, month)

    if formula_version == "v1":
        return base_score, metrics, breakdown

    # v2: positive_cap и penalty_factor поверх v1-метрик
    role = employee.role
    role_cfg = _get_role_config(role, formula_version="v2")

    # Позитивный потолок — сумма компонент breakdown, ограниченная positive_cap_max
    positive_cap_raw = float(
        breakdown.get("timeliness", 0.0)
        + breakdown.get("completion", 0.0)
        + breakdown.get("workload", 0.0)
        + breakdown.get("reliability", 0.0)
        + breakdown.get("management", 0.0)
    )

    positive_cap_max = float(role_cfg.positive_cap_max) if role_cfg else 100.0
    positive_cap = max(0.0, min(positive_cap_max, positive_cap_raw))

    penalty_factor = _compute_penalty_factor(role, metrics, role_cfg)
    final_score = round(positive_cap * penalty_factor, 2)

    # Расширяем метрики и разложение для аналитики
    extended_metrics = {
        **metrics,
        "v1_score": base_score,
        "positive_cap": positive_cap,
        "penalty_factor": penalty_factor,
        "formula_version": "v2",
    }
    extended_breakdown = {
        **breakdown,
        "positive_cap": round(positive_cap, 2),
        "penalty_factor": round(penalty_factor, 2),
        "v1_score": base_score,
    }

    return final_score, extended_metrics, extended_breakdown


@transaction.atomic
def generate_kpi_report(
    year: int,
    month: int,
    user: User,
    formula_version: str = "v1",
) -> KPIReport:
    """
    Сформировать (или пересчитать) KPI-отчет за месяц.
    - Создает/обновляет KPIReport.
    - Удаляет старые KPIResult этого отчета и пересчитывает заново.
    """
    if formula_version not in ("v1", "v2"):
        raise ValueError("Unsupported KPI formula_version: %s" % formula_version)

    report, created = KPIReport.objects.get_or_create(
        year=year,
        month=month,
        formula_version=formula_version,
        defaults={
            "generated_by": user,
            "status": "draft",
        },
    )

    # Если отчет уже был, пересчитываем результаты
    if not created:
        report.generated_by = user
        report.generated_at = timezone.now()
        report.status = "draft"
        report.message = ""
        report.save(update_fields=["generated_by", "generated_at", "status", "message"])

        KPIResult.objects.filter(report=report).delete()

    # Считаем KPI для всех сотрудников, у которых есть хотя бы одна задача
    employees_with_tasks = (
        Employee.objects.filter(tasks__isnull=False)
        .select_related("department", "user")
        .distinct()
    )

    for employee in employees_with_tasks:
        score, metrics, breakdown = calculate_employee_kpi(
            employee=employee,
            year=year,
            month=month,
            formula_version=formula_version,
        )

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

    report.status = "completed"
    report.save(update_fields=["status"])
    return report

