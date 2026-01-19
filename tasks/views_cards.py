from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required
import json
from .models import EventCard, Employee, Department, CardApproverOrder, Task
from .forms import EventCardForm, PlanReviewForm
from .decorators import role_required
from django.db.models import Q, Case, When, IntegerField


# Карточки мероприятий
@role_required("director", "deputy", "head", "senior")
def card_create(request):
    if request.method == "POST":
        form = EventCardForm(request.POST, request.FILES)
        if form.is_valid():
            card = form.save(commit=False)
            card.created_by = request.user.employee

            # Определяем статус карточки в зависимости от наличия плана
            if card.has_plan and card.plan_file:
                card.plan_status = "pending"
                card.plan_submitted_at = timezone.now()
                card.visible = False
            else:
                card.plan_status = "draft"
                card.visible = True

            card.save()
            form.save_m2m()

            # --- Удаляем старых и сохраняем новых согласующих ---
            CardApproverOrder.objects.filter(card=card).delete()
            approvers_ids = request.POST.getlist("approvers")

            for idx, emp_id in enumerate(approvers_ids, start=0):
                try:
                    emp = Employee.objects.get(id=emp_id)
                    CardApproverOrder.objects.create(card=card, employee=emp, order=idx)
                except Employee.DoesNotExist:
                    continue

            # --- Создаём первую задачу на согласование / утверждение ---
            if card.has_plan and card.plan_file:
                approver_orders = CardApproverOrder.objects.filter(card=card).order_by("order")

                if approver_orders.exists():
                    # есть согласующие → первая задача идёт первому
                    first_approver = approver_orders.first().employee
                    card.current_approver_index = 0
                    card.save(update_fields=["current_approver_index"])

                    Task.objects.create(
                        title=f"Согласовать план мероприятия «{card.title}»",
                        description="Необходимо рассмотреть загруженный план и утвердить или отклонить.",
                        card=card,
                        assigned_employee=first_approver,
                        created_by=request.user.employee,
                        task_type="approval",
                        priority="urgent",
                    )
                elif card.final_approver:
                    # нет согласующих → сразу финальному утверждающему
                    existing_task = Task.objects.filter(
                        card=card,
                        task_type="approval",
                        assigned_employee=card.final_approver
                    ).exists()

                    if not existing_task:
                        Task.objects.create(
                            title=f"Утвердить план мероприятия «{card.title}»",
                            description="План направлен напрямую утверждающему (без промежуточных согласующих).",
                            card=card,
                            assigned_employee=card.final_approver,
                            created_by=request.user.employee,
                            task_type="approval",
                            priority="normal",
                        )

                    card.current_approver_index = 0
                    card.save(update_fields=["current_approver_index"])

            messages.success(request, "Карточка успешно создана ✅")
            return redirect("task_list")

    else:
        initial = {"responsible_department": getattr(request.user.employee, "department", None)}
        form = EventCardForm(initial=initial)

    # --- Данные для выбора сотрудников и отделов (в модальном окне) ---
    employees_qs = Employee.objects.select_related("user").all().order_by("user__last_name", "user__first_name")
    employees_list = []
    for e in employees_qs:
        name = e.full_name or e.user.username
        if e.position:
            name = f"{name} — {e.position}"
        employees_list.append({"id": e.id, "name": name})

    departments_qs = Department.objects.all().order_by("name")
    depts_list = [{"id": d.id, "name": d.name} for d in departments_qs]

    return render(request, "tasks/card_create.html", {
        "form": form,
        "employees_json": json.dumps(employees_list, ensure_ascii=False),
        "departments_json": json.dumps(depts_list, ensure_ascii=False),
    })



@login_required
def card_detail(request, card_id):
    card = get_object_or_404(EventCard, pk=card_id)
    employee = request.user.employee
    effective_emp = employee.get_effective_employee()

    # --- Базовый queryset ---
    tasks_qs = card.tasks.select_related("assigned_employee", "assigned_department", "created_by")

    # --- Ролевая фильтрация ---
    if effective_emp.role in ("director", "deputy") or card.created_by == effective_emp:
        # 👑 Директор, зам или создатель карточки — видят всё
        tasks = tasks_qs
    elif effective_emp.role in ("head"):
        # 👩‍💼 Руководитель / старший — видят свои и сотрудников отдела
        tasks = tasks_qs.filter(
            Q(assigned_employee=effective_emp) |
            Q(assigned_department=effective_emp.department) |
            Q(created_by=effective_emp) |
            Q(recipients=effective_emp)
        ).distinct()
    else:
        # 👨‍💻 Обычный сотрудник — только свои задачи
        tasks = tasks_qs.filter(
            Q(assigned_employee=effective_emp) |
            Q(created_by=effective_emp) |
            Q(recipients=effective_emp)
        ).distinct()

    # --- Фильтрация по статусу ---
    filter_type = request.GET.get("filter", "all")

    if filter_type == "review":
        tasks = tasks.filter(task_type="review").exclude(status="done")
    elif filter_type == "urgent":
        tasks = tasks.filter(priority="urgent").exclude(status="done")
    elif filter_type == "new":
        tasks = tasks.filter(status="new")
    elif filter_type == "in_progress":
        tasks = tasks.filter(status="in_progress")
    elif filter_type == "done":
        tasks = tasks.filter(status="done")
    # иначе "all" — ничего не фильтруем

    # --- Сортировка ---
    tasks = tasks.order_by(
        Case(
            When(task_type="approval", then=0),
            When(task_type="review", then=1),
            When(priority="urgent", then=2),
            When(status="new", then=3),
            When(status="in_progress", then=4),
            When(status="done", then=5),
            default=6,
            output_field=IntegerField(),
        )
    )

    # --- Прогресс выполнения ---
    total = tasks_qs.count()
    done = tasks_qs.filter(status="done").count()
    progress = int((done / total) * 100) if total > 0 else 0

    # --- AJAX-подгрузка ---
    if request.GET.get("ajax") == "1":
        return render(request, "tasks/_task_list.html", {"tasks": tasks})

    # --- Контекст ---
    context = {
        "card": card,
        "tasks": tasks,
        "progress": progress,
        "filter_type": filter_type,
    }

    return render(request, "tasks/card_detail.html", context)




@login_required
def plan_review(request, card_id):
    card = get_object_or_404(EventCard, id=card_id)
    emp = request.user.employee
    effective_emp = emp.get_effective_employee()

    if effective_emp.role not in ("deputy", "director"):
        messages.error(request, "У вас нет прав на просмотр этой страницы.")
        return redirect("card_detail", card_id=card.id)

    if request.method == "POST":
        form = PlanReviewForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data["action"]
            reason = form.cleaned_data["reason"]

            if effective_emp.role == "deputy":
                if action == "approve":
                    card.plan_reviewed_by_deputy = effective_emp
                    card.plan_status = "pending"
                    card.plan_rejected_reason = ""
                else:
                    card.plan_reviewed_by_deputy = effective_emp
                    card.plan_status = "rejected"
                    card.plan_rejected_reason = reason
            elif effective_emp.role == "director":
                if action == "approve":
                    card.plan_reviewed_by_director = effective_emp
                    card.plan_status = "approved"
                    card.plan_approved_at = timezone.now()
                    card.visible = True
                else:
                    card.plan_reviewed_by_director = effective_emp
                    card.plan_status = "rejected"
                    card.plan_rejected_reason = reason
                    card.visible = False
            card.save()
            messages.success(request, "Решение по плану сохранено.")
            return redirect("card_detail", card_id=card.id)
    else:
        form = PlanReviewForm()

    return render(request, "tasks/plan_review.html", {"card": card, "form": form})
