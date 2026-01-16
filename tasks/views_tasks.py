from datetime import timedelta
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import json
import re

from .models import Task, TaskHistory, EventCard, Employee, CardApproverOrder, Category, TaskAttachment, Notification
from .forms import TaskForm
from .decorators import role_required

# 🔥 ВЕРНУЛИ ИМПОРТЫ ДЛЯ УВЕДОМЛЕНИЙ
from tasks.utils.notifications import notify
from .push import push_to_user


# =============================
# СПИСОК И ПРОСМОТР ЗАДАЧ
# =============================

@login_required
def task_list(request):
    """Главная страница — срочные задачи и доска мероприятий"""
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return render(request, "tasks/no_employee.html")

    effective_employee = employee.get_effective_employee()

    categories = Category.objects.all().order_by("name")

    active_category_slug = request.GET.get("category")
    active_category = None
    if active_category_slug:
        active_category = Category.objects.filter(slug=active_category_slug).first()

    # 🔎 Фильтр по сотруднику
    filter_emp_id = request.GET.get("employee")
    filter_emp = None
    if filter_emp_id:
        filter_emp = Employee.objects.filter(id=filter_emp_id).select_related("user", "department").first()

    today = timezone.now().date()
    urgent_deadline = today + timedelta(days=3)

    # 🔥 Срочные задачи (персональные)
    urgent_tasks_qs = Task.objects.filter(
        Q(assigned_employee=effective_employee) |
        Q(assigned_department=effective_employee.department) |
        Q(cc=effective_employee),
        Q(due_date__isnull=False),
        Q(due_date__lte=urgent_deadline),
        ~Q(status="done")
    ).distinct().order_by("due_date")

    if filter_emp:
        urgent_tasks_qs = urgent_tasks_qs.filter(
            Q(assigned_employee=filter_emp) | Q(created_by=filter_emp)
        )

    urgent_tasks = urgent_tasks_qs

    # 🧾 Задачи на утверждение (персональные)
    approval_tasks_qs = Task.objects.filter(
        assigned_employee=effective_employee,
        task_type__in=["approval", "review"]
    ).exclude(status="done").order_by("-created_at")

    if filter_emp:
        approval_tasks_qs = approval_tasks_qs.filter(
            Q(assigned_employee=filter_emp) | Q(created_by=filter_emp)
        )

    approval_tasks = approval_tasks_qs

    # 📋 Все карточки мероприятий
    cards_qs = EventCard.objects.all().prefetch_related("tasks", "categories").order_by("-start_date")

    if active_category:
        cards_qs = cards_qs.filter(categories=active_category)

    if filter_emp:
        cards_qs = cards_qs.filter(
            Q(created_by=filter_emp) | Q(tasks__assigned_employee=filter_emp)
        ).distinct()

    cards = cards_qs.distinct()

    # 📊 Добавляем счётчики
    for card in cards:
        tasks = card.tasks.all()
        card.approval_count = tasks.filter(task_type__in=["approval", "review"], status="new").count()
        card.urgent_count = tasks.filter(status="new", due_date__lte=today + timedelta(days=3)).count()
        card.other_count = tasks.exclude(status="done").count()
        card.done_count = tasks.filter(status="done").count()

    return render(request, "tasks/task_list.html", {
        "urgent_tasks": urgent_tasks,
        "approval_tasks": approval_tasks,
        "cards": cards,
        "categories": categories,
        "active_category": active_category,
        "filter_emp": filter_emp,
    })


@login_required
def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    employee = request.user.employee

    if (
        employee.role not in ("director", "deputy")
        and task.assigned_employee != employee
        and task.created_by != employee
    ):
        messages.error(request, "У вас нет доступа к этой задаче.")
        return redirect("task_list")

    history = task.history.order_by("-timestamp")
    attachments = task.attachments.order_by("-uploaded_at")

    context = {
        "task": task,
        "history": history,
        "attachments": attachments,
    }
    return render(request, "tasks/task_detail.html", context)


# =============================
# УПРАВЛЕНИЕ ЗАДАЧАМИ
# =============================

@login_required
def task_create_for_card(request, card_id):
    card = get_object_or_404(EventCard, pk=card_id)
    emp = request.user.employee

    if request.method == "POST":
        form = TaskForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            recipients = form.cleaned_data["recipients"]
            google_drive_link = form.cleaned_data.get("google_drive_link")
            attachment = form.cleaned_data.get("attachment")

            if not recipients:
                messages.error(request, "Выберите хотя бы одного адресата.")
                return redirect("task_create_for_card", card_id=card.id)

            for recipient in recipients:
                task = Task.objects.create(
                    card=card,
                    title=form.cleaned_data["title"],
                    description=form.cleaned_data["description"],
                    created_by=emp,
                    assigned_employee=recipient,
                    status="new",
                    due_date=form.cleaned_data["due_date"],
                    google_drive_link=google_drive_link,
                    priority="normal",
                )

                # 🔥 ВЕРНУЛИ ЛОГИКУ: Именные уведомления получателю
                if task.assigned_employee.user != request.user:
                    # Используем full_name (если есть в модели) или username
                    author_name = getattr(emp, 'full_name', emp.user.username)
                    
                    push_to_user(
                        task.assigned_employee.user,
                        "Новая задача 🆕",
                        f"{author_name} назначил(а) вам задачу «{task.title}»",
                        task.id
                    )
                    notify(
                        task.assigned_employee.user,
                        f"{author_name} назначил(а) вам задачу: {task.title}",
                        task.get_absolute_url()
                    )

                if attachment:
                    task.attachment = attachment
                    task.save(update_fields=["attachment"])

                task.recipients.add(recipient)

            messages.success(request, f"Создано {len(recipients)} задач(и).")
            return redirect("card_detail", card_id=card.id)
    else:
        form = TaskForm(user=request.user)

    employees_qs = Employee.objects.select_related("user").order_by("user__last_name", "user__first_name")
    employees_list = [
        {"id": e.id, "name": f"{e.user.first_name} {e.user.last_name} ({e.position or '—'})"}
        for e in employees_qs
    ]

    return render(request, "tasks/create_task.html", {
        "form": form,
        "card": card,
        "employees_json": json.dumps(employees_list, ensure_ascii=False),
    })


@login_required
def take_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    emp = request.user.employee
    effective_emp = emp.get_effective_employee()

    if task.assigned_employee and task.assigned_employee != effective_emp:
        messages.error(request, "Эта задача уже назначена другому сотруднику.")
        return redirect("task_list")

    if request.method == "POST":
        task.assigned_employee = effective_emp
        task.status = "in_progress"
        task.save()
        TaskHistory.objects.create(
            task=task,
            employee=effective_emp,
            action="taken",
            timestamp=timezone.now(),
        )

        # 🔥 ВЕРНУЛИ ЛОГИКУ: Уведомление создателю
        if task.created_by and task.created_by.user != request.user:
            author_name = getattr(effective_emp, 'full_name', effective_emp.user.username)
            push_to_user(
                task.created_by.user,
                "В работе ▶️",
                f"{author_name} взял(а) задачу «{task.title}» в работу",
                task.id
            )
            notify(
                task.created_by.user,
                f"{author_name} взял(а) задачу «{task.title}» в работу",
                task.get_absolute_url()
            )

        messages.success(request, "Задача принята в работу.")
        return redirect("task_list")

    return render(request, "tasks/task_detail.html", {"task": task})


@login_required
@transaction.atomic
def task_execute(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    employee = request.user.employee

    if task.assigned_employee != employee:
        messages.error(request, "Вы не можете выполнить эту задачу.")
        return redirect("task_detail", task_id=task.id)

    if task.status == "under_review":
        messages.warning(request, "Задача уже на рассмотрении.")
        return redirect("task_detail", task_id=task.id)

    if request.method == "POST":
        description = request.POST.get("execution_comment", "").strip()
        file = request.FILES.get("file")
        link = request.POST.get("link", "").strip()

        if task.status == "sent_for_review":
            action_label = "execution_updated"
            comment_text = description or "Исполнитель внёс изменения."
        else:
            action_label = "sent_for_review"
            comment_text = description or "Задача отправлена на согласование."

        TaskHistory.objects.create(
            task=task,
            employee=employee,
            action=action_label,
            comment=comment_text
        )

        if file:
            TaskAttachment.objects.create(task=task, file=file, uploaded_by=employee)
        if link:
            TaskAttachment.objects.create(task=task, link=link, uploaded_by=employee)

        task.status = "sent_for_review"
        task.save(update_fields=["status"])

        last_review = (
            Task.objects.filter(
                card=task.card,
                task_type="review",
                assigned_employee=task.created_by,
                description__icontains=f"[orig_task_id:{task.id}]"
            )
            .order_by("-created_at")
            .first()
        )

        emp_name = getattr(employee, 'full_name', employee.user.username)

        if not last_review or last_review.status == "done":
            review_task = Task.objects.create(
                title=f"Проверить выполнение задачи «{task.title}»",
                description=(
                    f"[orig_task_id:{task.id}]\n"
                    f"Исполнитель {emp_name} отправил материалы.\n\n{description or ''}"
                ),
                card=task.card,
                assigned_employee=task.created_by,
                created_by=employee,
                task_type="review",
                status="new",
                priority="normal",
            )
            TaskHistory.objects.create(task=review_task, employee=employee, action="created")
        else:
            last_review.description = (
                f"[orig_task_id:{task.id}]\n"
                f"Исполнитель обновил выполнение.\n\n{description or last_review.description}"
            )
            last_review.status = "new"
            last_review.save(update_fields=["description", "status"])
            TaskHistory.objects.create(task=last_review, employee=employee, action="execution_updated")

        # 🔥 ВЕРНУЛИ ЛОГИКУ: Уведомление руководителю
        if task.created_by and task.created_by.user != request.user:
            push_to_user(
                task.created_by.user,
                "На проверке 👀",
                f"{emp_name} отправил(а) задачу «{task.title}» на согласование",
                task.id
            )
            notify(
                task.created_by.user,
                f"{emp_name} отправил(а) задачу «{task.title}» на согласование",
                task.get_absolute_url()
            )

        messages.success(request, "Задача отправлена на согласование.")
        return redirect("task_list")

    return render(request, "tasks/task_execute.html", {"task": task})


@login_required
def task_review(request, task_id):
    review_task = get_object_or_404(Task, id=task_id)
    reviewer = request.user.employee

    if review_task.assigned_employee != reviewer and reviewer.role not in ("director", "deputy"):
        messages.error(request, "У вас нет доступа.")
        return redirect("task_list")

    if review_task.task_type != "review":
        return redirect("task_detail", task_id=review_task.id)

    base_task = None
    if review_task.description:
        m = re.search(r"\[orig_task_id\s*:\s*(\d+)\]", review_task.description)
        if m:
            try:
                base_task = Task.objects.filter(id=int(m.group(1))).first()
            except ValueError:
                base_task = None

    if not base_task:
        trimmed = review_task.title.replace("Проверить выполнение задачи", "").strip(" «»\"'")
        if trimmed:
            base_task = Task.objects.filter(
                card=review_task.card,
                title__icontains=trimmed
            ).exclude(id=review_task.id).order_by("-created_at").first()

    attachments = []
    last_exec_comment = None

    if base_task:
        last_exec = base_task.history.filter(
            action__in=["sent_for_review", "executed", "execution_updated"]
        ).order_by("-timestamp").first()

        if last_exec:
            last_exec_comment = last_exec.comment
            attachments = (
                base_task.attachments
                .filter(uploaded_at__gte=last_exec.timestamp)
                .order_by("uploaded_at")
            )

    if not base_task:
        messages.error(request, "Исходная задача не найдена.")
        return redirect("task_list")

    return render(request, "tasks/task_review.html", {
        "review_task": review_task,
        "base_task": base_task,
        "attachments": attachments,
        "last_exec_comment": last_exec_comment,
    })


@login_required
@transaction.atomic
def task_review_take(request, task_id):
    review_task = get_object_or_404(Task, id=task_id)
    reviewer = request.user.employee

    if review_task.assigned_employee != reviewer:
        messages.error(request, "Вы не можете взять эту задачу.")
        return redirect("task_list")

    base_task = None
    m = re.search(r"\[orig_task_id\s*:\s*(\d+)\]", review_task.description or "")
    if m:
        base_task = Task.objects.filter(id=int(m.group(1))).first()

    review_task.status = "in_progress"
    review_task.save(update_fields=["status"])
    TaskHistory.objects.create(task=review_task, employee=reviewer, action="in_progress")

    if base_task:
        base_task.status = "under_review"
        base_task.save(update_fields=["status"])
        TaskHistory.objects.create(task=base_task, employee=reviewer, action="under_review")

        # 🔥 ВЕРНУЛИ ЛОГИКУ: Уведомление исполнителю
        if base_task.assigned_employee and base_task.assigned_employee.user != request.user:
            rev_name = getattr(reviewer, 'full_name', reviewer.user.username)
            push_to_user(
                base_task.assigned_employee.user,
                "Проверка 🧐",
                f"{rev_name} начал(а) проверку задачи «{base_task.title}»",
                base_task.id
            )
            notify(
                base_task.assigned_employee.user,
                f"{rev_name} начал(а) проверку задачи «{base_task.title}»",
                base_task.get_absolute_url()
            )

    messages.success(request, "Вы взяли задачу на проверку.")
    return redirect("task_review", task_id=review_task.id)


@login_required
@transaction.atomic
def task_review_approve(request, task_id):
    review_task = get_object_or_404(Task, id=task_id)
    reviewer = request.user.employee

    base_task = None
    m = re.search(r"\[orig_task_id\s*:\s*(\d+)\]", review_task.description or "")
    if m:
        base_task = Task.objects.filter(id=int(m.group(1))).first()

    comment = request.POST.get("comment", "").strip()

    review_task.status = "done"
    review_task.save(update_fields=["status"])
    TaskHistory.objects.create(task=review_task, employee=reviewer, action="done")

    if base_task:
        base_task.status = "done"
        base_task.review_comment = comment or "Задача утверждена."
        base_task.save(update_fields=["status", "review_comment"])
        TaskHistory.objects.create(task=base_task, employee=reviewer, action="approved")

        # 🔥 ВЕРНУЛИ ЛОГИКУ: Уведомление исполнителю
        if base_task.assigned_employee and base_task.assigned_employee.user != request.user:
            rev_name = getattr(reviewer, 'full_name', reviewer.user.username)
            push_to_user(
                base_task.assigned_employee.user,
                "Утверждено ✅",
                f"{rev_name} утвердил(а) задачу «{base_task.title}»",
                base_task.id
            )
            notify(
                base_task.assigned_employee.user,
                f"{rev_name} утвердил(а) задачу «{base_task.title}»",
                base_task.get_absolute_url()
            )

    messages.success(request, "Задача утверждена.")
    return redirect("task_list")


@login_required
@transaction.atomic
def task_review_reject(request, task_id):
    review_task = get_object_or_404(Task, id=task_id)
    reviewer = request.user.employee

    base_task = None
    m = re.search(r"\[orig_task_id\s*:\s*(\d+)\]", review_task.description or "")
    if m:
        base_task = Task.objects.filter(id=int(m.group(1))).first()

    comment = request.POST.get("comment", "").strip()

    if not base_task:
        return redirect("task_list")

    review_task.status = "done"
    review_task.save(update_fields=["status"])
    TaskHistory.objects.create(task=review_task, employee=reviewer, action="done")

    base_task.status = "rejected"
    base_task.review_comment = comment or "Задача возвращена."
    base_task.save(update_fields=["status", "review_comment"])
    TaskHistory.objects.create(task=base_task, employee=reviewer, action="rejected")

    # 🔥 ВЕРНУЛИ ЛОГИКУ: Уведомление исполнителю
    if base_task.assigned_employee and base_task.assigned_employee.user != request.user:
        rev_name = getattr(reviewer, 'full_name', reviewer.user.username)
        push_to_user(
            base_task.assigned_employee.user,
            "На доработку 🔁",
            f"{rev_name} вернул(а) задачу «{base_task.title}» на доработку",
            base_task.id
        )
        notify(
            base_task.assigned_employee.user,
            f"{rev_name} вернул(а) задачу «{base_task.title}» на доработку",
            base_task.get_absolute_url()
        )

    messages.warning(request, "Задача возвращена на доработку.")
    return redirect("task_list")


@login_required
@transaction.atomic
def approve_plan(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    emp = request.user.employee
    effective_emp = emp.get_effective_employee()

    if task.task_type != "approval":
        return redirect("task_list")

    card = task.card
    approver_orders = CardApproverOrder.objects.filter(card=card).order_by("order")
    approvers = [rel.employee for rel in approver_orders]
    total_approvers = len(approvers)

    if request.method == "POST":
        current_order = next((rel for rel in approver_orders if rel.employee == effective_emp), None)
        is_final_approver = card.final_approver == effective_emp

        if not current_order and not is_final_approver:
            messages.error(request, "Вы не являетесь согласующим.")
            return redirect("task_list")

        task.status = "done"
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "completed_at"])
        TaskHistory.objects.create(task=task, employee=effective_emp, action="approved")

        approver_name = getattr(effective_emp, 'full_name', effective_emp.user.username)

        if is_final_approver:
            card.plan_status = "approved"
            card.plan_approved_at = timezone.now()
            card.visible = True
            card.is_fully_approved = True
            card.current_approver_index = total_approvers + 1
            card.save(update_fields=["plan_status", "plan_approved_at", "visible", "is_fully_approved", "current_approver_index"])
            
            # 🔥 Уведомление автору
            notify(card.created_by.user, f"{approver_name} утвердил план: {card.title}", card.get_absolute_url())
            
            messages.success(request, "План утверждён.")
            return redirect("task_list")

        current_index = current_order.order
        next_order = approver_orders.filter(order=current_index + 1).first()

        if next_order:
            next_emp = next_order.employee
            task_n = Task.objects.create(
                title=f"Согласовать план «{card.title}»",
                description="План прошёл предыдущего согласующего.",
                card=card,
                assigned_employee=next_emp,
                created_by=effective_emp,
                task_type="approval",
                priority="normal",
                attachment=card.plan_file,
            )
            card.current_approver_index = current_index + 1
            card.save(update_fields=["current_approver_index"])
            
            # 🔥 Уведомление следующему
            notify(next_emp.user, f"Вам поступил план на согласование: {card.title}", task_n.get_absolute_url())
            
            messages.success(request, f"Передано: {next_emp.user.get_full_name()}")
        else:
            if card.final_approver:
                existing_task = Task.objects.filter(card=card, task_type="approval", assigned_employee=card.final_approver).exists()
                if not existing_task:
                    task_n = Task.objects.create(
                        title=f"Утвердить план «{card.title}»",
                        description="План на утверждение.",
                        card=card,
                        assigned_employee=card.final_approver,
                        created_by=effective_emp,
                        task_type="approval",
                        priority="urgent",
                        attachment=card.plan_file,
                    )
                    card.current_approver_index = total_approvers
                    card.save(update_fields=["current_approver_index"])
                    
                    # 🔥 Уведомление финальному
                    notify(card.final_approver.user, f"План на финальное утверждение: {card.title}", task_n.get_absolute_url())
                    
                    messages.success(request, f"Передано утверждающему: {card.final_approver.user.get_full_name()}")
            else:
                card.plan_status = "approved"
                card.plan_approved_at = timezone.now()
                card.visible = True
                card.is_fully_approved = True
                card.current_approver_index = total_approvers
                card.save(update_fields=["plan_status", "plan_approved_at", "visible", "is_fully_approved", "current_approver_index"])
                
                # 🔥 Уведомление автору
                notify(card.created_by.user, f"План полностью согласован: {card.title}", card.get_absolute_url())
                
                messages.success(request, "План согласован.")

        return redirect("task_list")

    return render(request, "tasks/approve_plan.html", {"task": task, "card": card})


@login_required
def reject_plan(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    emp = request.user.employee
    effective_emp = emp.get_effective_employee()
    card = task.card

    if request.method == "POST":
        reason = request.POST.get("reason", "") or request.POST.get("comment", "")
        task.status = "rejected"
        task.save(update_fields=["status"])
        TaskHistory.objects.create(task=task, employee=effective_emp, action="rejected")

        card.plan_status = "rejected"
        card.plan_rejected_reason = reason
        card.visible = False
        card.save(update_fields=["plan_status", "plan_rejected_reason", "visible"])

        # 🔥 Уведомление автору
        emp_name = getattr(effective_emp, 'full_name', effective_emp.user.username)
        notify(card.created_by.user, f"{emp_name} отклонил план: {card.title}", card.get_absolute_url())

        messages.warning(request, "План отклонён.")
        return redirect("task_list")

    return render(request, "tasks/reject_plan.html", {"task": task, "card": card})


@login_required
def send_plan_again(request, card_id):
    card = get_object_or_404(EventCard, id=card_id)
    emp = request.user.employee
    if card.created_by != emp:
        return redirect("card_detail", card_id=card.id)

    if request.method == "POST":
        new_file = request.FILES.get("plan_file")
        if new_file:
            card.plan_file = new_file

        card.plan_status = "pending"
        card.visible = False
        card.current_approver_index = 0
        card.save()

        emp_name = getattr(emp, 'full_name', emp.user.username)

        first_rel = card.cardapproverorder_set.order_by("order").first()
        if first_rel:
            task = Task.objects.create(
                title=f"Согласовать план «{card.title}»",
                description="План обновлён.",
                status="new",
                task_type="approval",
                assigned_employee=first_rel.employee,
                created_by=emp,
                priority="urgent",
                card=card,
                attachment=new_file,
            )
            # 🔥 Уведомление
            notify(first_rel.employee.user, f"План отправлен повторно: {card.title}", task.get_absolute_url())
        elif card.final_approver:
            task = Task.objects.create(
                title=f"Утвердить план «{card.title}»",
                description="План обновлён.",
                status="new",
                task_type="approval",
                assigned_employee=card.final_approver,
                created_by=emp,
                priority="urgent",
                card=card,
                attachment=new_file,
            )
            # 🔥 Уведомление
            notify(card.final_approver.user, f"План отправлен повторно: {card.title}", task.get_absolute_url())

        messages.success(request, "План отправлен повторно.")
        return redirect("card_detail", card_id=card.id)

    return redirect("card_detail", card_id=card.id)


@login_required
def delegate_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    emp = request.user.employee
    if request.method == "POST":
        delegate_id = request.POST.get("delegate_to")
        try:
            delegate = Employee.objects.get(id=delegate_id)
            old_emp = task.assigned_employee
            
            task.assigned_employee = delegate
            task.save(update_fields=["assigned_employee"])
            TaskHistory.objects.create(task=task, employee=emp, action="delegated")
            
            # 🔥 Уведомление новому исполнителю
            if old_emp != delegate and delegate.user != request.user:
                emp_name = getattr(emp, 'full_name', emp.user.username)
                push_to_user(
                    delegate.user, 
                    "Новая задача", 
                    f"{emp_name} делегировал(а) вам задачу «{task.title}»", 
                    task.id
                )

            messages.success(request, "Задача успешно делегирована.")
        except Employee.DoesNotExist:
            messages.error(request, "Выбранный сотрудник не найден.")
        return redirect("task_list")

    employees = Employee.objects.exclude(id=emp.id)
    return render(request, "tasks/delegate_task.html", {"task": task, "employees": employees})


@login_required
def complete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    emp = request.user.employee

    if request.method == "POST":
        task.status = "done"
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "completed_at"])
        TaskHistory.objects.create(task=task, employee=emp, action="completed")
        
        # 🔥 Уведомление создателю
        if task.created_by and task.created_by.user != request.user:
            emp_name = getattr(emp, 'full_name', emp.user.username)
            push_to_user(
                task.created_by.user,
                "Завершено ✅",
                f"{emp_name} завершил(а) задачу «{task.title}»",
                task.id
            )
            notify(
                task.created_by.user,
                f"{emp_name} завершил(а) задачу «{task.title}»",
                task.get_absolute_url()
            )

        messages.success(request, "Задача завершена.")
        return redirect("task_list")

    return render(request, "tasks/complete_confirm.html", {"task": task})


# 🔥 ВЕРНУЛИ ФУНКЦИИ ДЛЯ СТРАНИЦЫ УВЕДОМЛЕНИЙ (КОЛОКОЛЬЧИК)
@login_required
def notifications_list(request):
    notes = request.user.notifications.order_by("-created_at")
    unread_count = notes.filter(is_read=False).count()
    return render(request, "notifications/list.html", {
        "notes": notes,
        "unread_count": unread_count
    })

@login_required
def notification_read(request, note_id):
    n = get_object_or_404(Notification, id=note_id, user=request.user)
    n.is_read = True
    n.save(update_fields=["is_read"])
    if n.url:
        return redirect(n.url)
    return redirect("notifications")

@login_required
def notifications_read_all(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect("notifications")