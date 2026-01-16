import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from datetime import date, timedelta
from django.db.models import Q
from .models import Task, Employee, EventCard, Department, TaskHistory, CardApproverOrder
from .forms import TaskForm, EventCardForm, PlanReviewForm
from .decorators import role_required

# helper: проверка ролей
def user_has_role(user, roles):
    try:
        emp = user.employee
    except Employee.DoesNotExist:
        return False
    return emp.role in roles

# @staff_member_required
# def employee_list(request):
#     """Список сотрудников (для админов)"""
#     employees = Employee.objects.select_related('department', 'user').all()
#     return render(request, "tasks/employee_list.html", {
#         "employees": employees
#     })
#
# @login_required
# def frozen_notice(request):
#     return render(request, 'tasks/frozen_notice.html')

# @login_required
# def task_list(request):
#     """Главная страница — срочные задачи и доска мероприятий"""
#     try:
#         employee = request.user.employee
#     except Employee.DoesNotExist:
#         return render(request, "tasks/no_employee.html")
#
#      # 🧠 если кто-то замещает этого сотрудника, показываем задачи замещаемого
#     effective_employee = employee.get_effective_employee()
#
#     today = timezone.now().date()
#     urgent_deadline = today + timedelta(days=3)
#
#     # 🔥 Срочные задачи
#     urgent_tasks = Task.objects.filter(
#         Q(assigned_employee=effective_employee) |
#         Q(assigned_department=effective_employee.department) |
#         Q(cc=effective_employee),
#         Q(due_date__lte=urgent_deadline),
#         ~Q(status="done")
#     ).distinct().order_by("due_date")
#
#     # Задачи на утверждение
#     approval_tasks = Task.objects.filter(
#         assigned_employee=effective_employee,
#         task_type="approval",
#     ).exclude(status="done").order_by("-created_at")
#
#     # 📋 Карточки мероприятий, связанные с пользователем
#     cards = EventCard.objects.filter(
#         Q(tasks__assigned_employee=effective_employee) |
#         Q(tasks__assigned_department=effective_employee.department) |
#         Q(tasks__cc=effective_employee) |
#         Q(created_by=effective_employee)
#     ).distinct().order_by('-start_date')
#
#     return render(request, "tasks/task_list.html", {
#         "urgent_tasks": urgent_tasks,
#         "cards": cards,
#         "approval_tasks": approval_tasks,
#     })

# @role_required("director", "deputy")
# def plan_review(request, card_id):
#     card = get_object_or_404(EventCard, id=card_id)
#     emp = request.user.employee
#     effective_emp = emp.get_effective_employee()
#
#     # обработка POST остаётся как есть, но замены добавим в местах проверки роли
#     if request.method == "POST":
#         form = PlanReviewForm(request.POST)
#         if form.is_valid():
#             action = form.cleaned_data["action"]
#             reason = form.cleaned_data["reason"]
#
#             # теперь работаем через effective_emp
#             if effective_emp.role == "deputy":
#                 # заместитель (или тот, кто его замещает)
#                 if action == "approve":
#                     card.plan_reviewed_by_deputy = effective_emp
#                     card.plan_status = "pending"
#                     card.plan_rejected_reason = ""
#                     card.save()
#                     messages.success(request, "План одобрен заместителем. Далее — утверждение директором.")
#                 else:
#                     card.plan_reviewed_by_deputy = effective_emp
#                     card.plan_status = "rejected"
#                     card.plan_rejected_reason = reason
#                     card.save()
#                     messages.success(request, "План отклонён заместителем.")
#
#             elif effective_emp.role == "director":
#                 if action == "approve":
#                     card.plan_reviewed_by_director = effective_emp
#                     card.plan_status = "approved"
#                     card.plan_approved_at = timezone.now()
#                     card.visible = True
#                     card.save()
#                     messages.success(request, "План утверждён директором. Карточка доступна для задач.")
#                 else:
#                     card.plan_reviewed_by_director = effective_emp
#                     card.plan_status = "rejected"
#                     card.plan_rejected_reason = reason
#                     card.visible = False
#                     card.save()
#                     messages.success(request, "План отклонён директором.")
#             return redirect("card_detail", card_id=card.id)
#     else:
#         form = PlanReviewForm()
#
#     return render(request, "tasks/plan_review.html", {"card": card, "form": form})

# def card_detail(request, card_id):
#     card = get_object_or_404(EventCard, pk=card_id)
#     tasks = card.tasks.all()  # или Task.objects.filter(card=card)
#     total = tasks.count()
#     done = tasks.filter(status="done").count()
#     progress = int((done / total) * 100) if total > 0 else 0
#
#     return render(request, "tasks/card_detail.html", {
#         "card": card,
#         "tasks": tasks,
#         "progress": progress,
#     })

# views.py
from django.db.models import Case, When
# import json
# from django.utils import timezone
# from django.contrib import messages
# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.decorators import login_required

# @role_required("director", "deputy", "head", "senior")
# def card_create(request):
#     if request.method == "POST":
#         form = EventCardForm(request.POST, request.FILES)
#         if form.is_valid():
#             card = form.save(commit=False)
#             card.created_by = request.user.employee
#
#             if card.has_plan and card.plan_file:
#                 card.plan_status = "pending"
#                 card.plan_submitted_at = timezone.now()
#                 card.visible = False
#             else:
#                 card.plan_status = "draft"
#                 card.visible = True
#
#             card.save()
#             form.save_m2m()
#
#             # --- сохраняем порядок согласующих ---
#             CardApproverOrder.objects.filter(card=card).delete()
#             approvers_ids = request.POST.getlist("approvers")
#
#             for idx, emp_id in enumerate(approvers_ids, start=0):  # нумерация с 0
#                 try:
#                     emp = Employee.objects.get(id=emp_id)
#                     CardApproverOrder.objects.create(card=card, employee=emp, order=idx)
#                 except Employee.DoesNotExist:
#                     continue
#
#             # --- логика рассылки задач ---
#             if card.has_plan and card.plan_file:
#                 approver_orders = CardApproverOrder.objects.filter(card=card).order_by("order")
#
#                 if approver_orders.exists():
#                     first_approver = approver_orders.first().employee
#                     card.current_approver_index = 0
#                     card.save(update_fields=["current_approver_index"])
#
#                     Task.objects.create(
#                         title=f"Согласовать план мероприятия «{card.title}»",
#                         description="Необходимо рассмотреть загруженный план и утвердить или отклонить.",
#                         card=card,
#                         assigned_employee=first_approver,
#                         created_by=request.user.employee,
#                         task_type="approval",
#                         priority="urgent",
#                     )
#
#                 elif card.final_approver:
#                     Task.objects.create(
#                         title=f"Утвердить план мероприятия «{card.title}»",
#                         description="План направлен на утверждение.",
#                         card=card,
#                         assigned_employee=card.final_approver,
#                         created_by=request.user.employee,
#                         task_type="approval",
#                         priority="urgent",
#                     )
#
#             messages.success(request, "Карточка создана.")
#             return redirect("task_list")
#
#     else:
#         initial = {}
#         try:
#             initial["responsible_department"] = request.user.employee.department
#         except Exception:
#             pass
#         form = EventCardForm(initial=initial)
#
#     # --- подготовка данных для выбора сотрудников и отделов ---
#     employees_qs = Employee.objects.select_related('user').all().order_by('user__last_name', 'user__first_name')
#     employees_list = []
#     for e in employees_qs:
#         fname = e.user.first_name or ""
#         lname = e.user.last_name or ""
#         display = f"{fname} {lname}".strip() or e.user.username
#         if e.position:
#             display = f"{display} — {e.position}"
#         employees_list.append({"id": e.id, "name": display})
#
#     departments_qs = Department.objects.all().order_by('name')
#     depts_list = [{"id": d.id, "name": d.name} for d in departments_qs]
#
#     context = {
#         "form": form,
#         "employees_json": json.dumps(employees_list, ensure_ascii=False),
#         "departments_json": json.dumps(depts_list, ensure_ascii=False),
#     }
#     return render(request, "tasks/card_create.html", context)



# убедись, что вверху файла импортированы модели
# from .models import Task, EventCard, CardApproverOrder, Employee

# @login_required
# def approve_plan(request, task_id):
#     """
#     Обработка согласования: текущая approval-задача закрывается,
#     создаётся задача следующему согласующему или финальному утверждающему.
#     Исправления: НЕ записываем None в current_approver_index — используем числовой индекс.
#     """
#     task = get_object_or_404(Task, id=task_id, task_type="approval")
#     card = task.card
#     employee = request.user.employee
#
#     # Получаем список согласующих в правильном порядке (через CardApproverOrder.order)
#     approver_rel_qs = card.cardapproverorder_set.select_related("employee").order_by("order")
#     approvers = [rel.employee for rel in approver_rel_qs]
#
#     # Закрываем текущую approval-задачу
#     task.status = "done"
#     task.save(update_fields=["status"])
#
#     # Если текущий пользователь — финальный утверждающий, утверждаем окончательно
#     if card.final_approver and card.final_approver == employee:
#         card.plan_status = "approved"
#         card.visible = True
#         card.is_fully_approved = True
#         card.plan_approved_at = timezone.now()
#         # ставим индекс = количество согласующих, чтобы явно отметить "всё пройдено"
#         card.current_approver_index = len(approvers)
#         card.save(update_fields=["plan_status", "visible", "is_fully_approved", "plan_approved_at", "current_approver_index"])
#
#         # закрыть оставшиеся висящие approval-задачи по этой карточке (если есть)
#         Task.objects.filter(card=card, task_type="approval").exclude(id=task.id).update(status="done")
#
#         messages.success(request, f"План «{card.title}» успешно утверждён.")
#         return redirect("task_list")
#
#     # иначе — двигаемся по списку согласующих
#     current_index = card.current_approver_index if card.current_approver_index is not None else 0
#     next_index = current_index + 1
#
#     if next_index < len(approvers):
#         # есть следующий согласующий — назначаем ему задачу
#         next_approver = approvers[next_index]
#         card.current_approver_index = next_index
#         card.save(update_fields=["current_approver_index"])
#
#         Task.objects.create(
#             title=f"Согласовать план мероприятия «{card.title}»",
#             description="План передан следующему согласующему.",
#             card=card,
#             assigned_employee=next_approver,
#             created_by=employee,
#             task_type="approval",
#             priority="urgent",
#         )
#
#         messages.success(request, f"План передан следующему согласующему: {next_approver.user.get_full_name() or next_approver.user.username}.")
#         return redirect("task_list")
#
#     # если согласователи закончились — отправляем финальному утверждающему (если есть)
#     if card.final_approver:
#         # пометить, что все согласователи пройдены ( индекс = len(approvers) )
#         card.current_approver_index = len(approvers)
#         card.save(update_fields=["current_approver_index"])
#
#         Task.objects.create(
#             title=f"Утвердить план мероприятия «{card.title}»",
#             description="Все согласующие утвердили, требуется финальное утверждение.",
#             card=card,
#             assigned_employee=card.final_approver,
#             created_by=employee,
#             task_type="approval",
#             priority="urgent",
#         )
#
#         messages.success(request, "План направлен на финальное утверждение.")
#         return redirect("task_list")
#
#     # если нет финального утверждающего — закрываем процесс согласования полностью
#     card.is_fully_approved = True
#     card.plan_status = "approved"
#     card.visible = True
#     card.plan_approved_at = timezone.now()
#     card.current_approver_index = len(approvers)
#     card.save(update_fields=["is_fully_approved", "plan_status", "visible", "plan_approved_at", "current_approver_index"])
#
#     # закрываем все approval-задачи по карточке
#     Task.objects.filter(card=card, task_type="approval").exclude(id=task.id).update(status="done")
#
#     messages.success(request, f"План «{card.title}» полностью согласован.")
#     return redirect("task_list")




# @login_required
# def reject_plan(request, task_id):
#     task = get_object_or_404(Task, id=task_id, task_type="approval")
#     card = task.card
#     employee = request.user.employee
#
#     if request.method == "POST":
#         comment = request.POST.get("comment", "").strip()
#
#         task.status = "done"
#         task.completed_at = timezone.now()
#         task.save(update_fields=["status", "completed_at"])
#
#         card.plan_status = "rejected"
#         card.visible = True  # чтобы автор мог снова редактировать
#         card.is_fully_approved = False
#         card.save(update_fields=["plan_status", "visible", "is_fully_approved"])
#
#         # если у тебя есть история, можно добавить:
#         try:
#             TaskHistory.objects.create(
#                 task=task,
#                 action="rejected",
#                 performed_by=employee,
#                 comment=comment or "План возвращён на доработку",
#             )
#         except:
#             pass
#
#         messages.warning(request, f"План «{card.title}» возвращён на доработку.")
#         return redirect("task_list")
#
#     return render(request, "tasks/reject_plan.html", {"task": task, "card": card})


# @login_required
# def task_detail(request, task_id):
#     task = get_object_or_404(Task, id=task_id)
#     employee = request.user.employee
#
#     available_employees = []
#     if employee.role == "deputy":
#         available_employees = Employee.objects.filter(role__in=["head", "senior", "staff"])
#     elif employee.role == "head":
#         available_employees = Employee.objects.filter(department=employee.department).exclude(id=employee.id)
#
#     return render(request, "tasks/task_detail.html", {
#         "task": task,
#         "available_employees": available_employees,
#     })


# @login_required
# def task_execute(request, task_id):
#     task = get_object_or_404(Task, id=task_id)
#
#     if task.assigned_employee != request.user.employee:
#         messages.error(request, "Вы не можете выполнить эту задачу.")
#         return redirect("task_list")
#
#     if request.method == "POST":
#         action = request.POST.get("action")
#         comment = request.POST.get("comment", "").strip()
#
#         if action == "approve":
#             task.status = "done"
#             task.save()
#
#             # Если это согласование плана
#             if task.task_type == "approval":
#                 card = task.card
#                 if card.plan_status == "pending":
#                     card.plan_status = "approved_by_deputy"
#                     # Создать задачу для директора
#                     director = Employee.objects.filter(role="director").first()
#                     if director:
#                         Task.objects.create(
#                             title=f"Утвердить план мероприятия «{card.title}»",
#                             description="План одобрен заместителем, требуется утверждение директором.",
#                             card=card,
#                             assigned_employee=director,
#                             created_by=request.user.employee,
#                             task_type="approval",
#                             priority="urgent",
#                         )
#                 elif card.plan_status == "approved_by_deputy":
#                     card.plan_status = "approved"
#                     card.plan_approved_at = timezone.now()
#                     card.visible = True
#                 card.save()
#
#             messages.success(request, "Задача выполнена и согласована.")
#         elif action == "reject":
#             task.status = "rejected"
#             task.save()
#             card = task.card
#             card.plan_status = "rejected"
#             card.plan_rejected_reason = comment
#             card.save()
#             messages.warning(request, "План отклонён, причина сохранена.")
#         return redirect("task_list")
#
#     return render(request, "tasks/task_execute.html", {"task": task})

# @login_required
# def complete_task(request, card_id):
#     """Завершить задачу"""
#     try:
#         employee = request.user.employee
#     except Employee.DoesNotExist:
#         messages.error(request, "Ваш профиль сотрудника не найден.")
#         return redirect("task_list")
#
#     task = get_object_or_404(Task, id=card_id, assigned_employee=employee)
#     task.status = "done"
#     task.save()
#
#     messages.success(request, "Задача отмечена как выполненная ✅")
#     return redirect("task_list")

# @login_required
# def create_task(request):
#     card_id = request.GET.get("card")  # 👈 Проверяем, передан ли ID карточки
#     card = None
#
#     if card_id:
#         card = get_object_or_404(EventCard, id=card_id)
#
#     if request.method == "POST":
#         form = TaskForm(request.POST, user=request.user)
#         if form.is_valid():
#             task = form.save(commit=False)
#             task.created_by = request.user
#             if card:
#                 task.event_card = card  # 👈 Автоматически привязываем задачу к карточке
#             task.save()
#             form.save_m2m()
#             return redirect("card_detail", card_id=card.id) if card else redirect("task_list")
#     else:
#         form = TaskForm(user=request.user)
#
#     return render(request, "tasks/create_task.html", {
#         "form": form,
#         "card": card,
#     })

# @login_required
# def task_create_for_card(request, card_id):
#     card = get_object_or_404(EventCard, id=card_id)
#     if not card.visible:
#         messages.error(request, "Карточка ещё не утверждена — задачи создавать нельзя.")
#         return redirect("card_detail", card_id=card.id)
#
#     if not card.can_user_create_task(request.user):
#         messages.error(request, "У вас нет прав создавать задачи в этой карточке.")
#         return redirect("card_detail", card_id=card.id)
#
#     employee = request.user.employee
#
#     if request.method == "POST":
#         form = TaskForm(request.POST, user=employee)
#         if form.is_valid():
#             task = form.save(commit=False)
#             task.created_by = employee
#             task.card = card
#
#             # 👇 Автоматически проставляем назначенного сотрудника и департамент
#             assigned_emp = form.cleaned_data.get("assigned_employee")
#             recipients = form.cleaned_data.get("recipients")
#
#             # Если явно выбран адресат — используем его
#             if assigned_emp:
#                 task.assigned_employee = assigned_emp
#                 task.assigned_department = assigned_emp.department
#             # Иначе, если адресаты указаны — берем первого из них (обычно один)
#             elif recipients.exists():
#                 first_recipient = recipients.first()
#                 task.assigned_employee = first_recipient
#                 task.assigned_department = first_recipient.department
#
#             if employee.role == "staff":
#                 task.status = "new"
#
#             task.save()
#             form.save_m2m()
#             messages.success(request, "Задача создана.")
#             return redirect("card_detail", card_id=card.id)
#     else:
#         form = TaskForm(user=employee)
#
#     return render(request, "tasks/create_task.html", {"form": form, "card": card})

# @login_required
# def take_task(request, task_id):
#     task = get_object_or_404(Task, id=task_id)
#     employee = request.user.employee
#
#     if request.method == "POST" and task.assigned_employee == employee:
#         task.status = "in_progress"
#         task.save()
#         messages.success(request, "Задача взята в работу.")
#
#     TaskHistory.objects.create(task=task, employee=employee, action="in_progress")
    
    # return redirect("task_detail", task_id=task.id)

# @login_required
# def delegate_task(request, task_id):
#     task = get_object_or_404(Task, id=task_id)
#     employee = request.user.employee
#
#     # --- Ограничения доступа ---
#     # Только текущий исполнитель может перенаправлять
#     if task.assigned_employee != employee:
#         return redirect("task_detail", task_id=task.id)
#
#     # Задача должна быть "новой"
#     if task.status != "new":
#         return redirect("task_detail", task_id=task.id)
#
#     # Нельзя направлять задачи на согласование
#     if task.task_type == "approval":
#         return redirect("task_detail", task_id=task.id)
#
#     if request.method == "POST":
#         delegate_to_id = request.POST.get("delegate_to")
#         if not delegate_to_id:
#             messages.error(request, "Не выбран сотрудник.")
#             return redirect("task_detail", task_id=task.id)
#
#         delegate_to = get_object_or_404(Employee, id=delegate_to_id)
#
#         # Правила: зам может любому ниже, начальник отдела — только из своего отдела
#         if employee.role == "deputy":
#             if delegate_to.role not in ["head", "senior", "staff"]:
#                 messages.error(request, "Вы не можете направить задачу этому сотруднику.")
#                 return redirect("task_detail", task_id=task.id)
#         elif employee.role == "head":
#             if delegate_to.department != employee.department:
#                 messages.error(request, "Можно направлять только сотрудникам своего отдела.")
#                 return redirect("task_detail", task_id=task.id)
#
#         # --- Само перенаправление ---
#         task.assigned_employee = delegate_to
#         task.assigned_department = delegate_to.department
#         task.status = "new"
#         task.save()
#
#         messages.success(
#             request,
#             f"Задача направлена {delegate_to.user.last_name} {delegate_to.user.first_name}."
#         )
#         return redirect("task_detail", task_id=task.id)
#
#     return redirect("task_detail", task_id=task.id)


# @login_required
# def my_delegation(request):
#     employee = Employee.objects.get(user=request.user)
#
#     # Если сотрудник из отдела — показываем только коллег
#     if employee.department:
#         employees = Employee.objects.filter(department=employee.department).exclude(id=employee.id)
#     else:
#         employees = Employee.objects.none()
#
#     # ✅ Отмена замещения
#     if "cancel_delegation" in request.POST:
#         employee.delegate_to = None
#         employee.delegate_until = None
#         employee.save()
#         messages.success(request, "Вы отменили замещение. Доступ полностью восстановлен.")
#         return redirect("my_delegation")
#
#     # ✅ Создание нового замещения
#     if request.method == "POST" and "delegate_to" in request.POST:
#         delegate_to_id = request.POST.get("delegate_to")
#         delegate_until = request.POST.get("delegate_until")
#
#         if not delegate_to_id or not delegate_until:
#             messages.error(request, "Выберите замещающего и укажите дату окончания замещения.")
#         else:
#             try:
#                 delegate_to = Employee.objects.get(id=delegate_to_id, department=employee.department)
#             except Employee.DoesNotExist:
#                 messages.error(request, "Можно выбрать только коллегу из вашего отдела.")
#                 return redirect("my_delegation")
#
#             employee.delegate_to = delegate_to
#             employee.delegate_until = delegate_until
#             employee.save()
#             messages.success(request, f"Вы успешно передали свои полномочия {delegate_to}.")
#             return redirect("my_delegation")
#
#     active_delegate = employee.get_active_delegate()
#     delegated_from = Employee.objects.filter(delegate_to=employee, delegate_until__gte=timezone.now().date()).first()
#
#     context = {
#         "employee": employee,
#         "employees": employees,
#         "active_delegate": active_delegate,  # кого он выбрал
#         "delegated_from": delegated_from,    # кого он замещает
#     }
#     return render(request, "tasks/my_delegation.html", context)
