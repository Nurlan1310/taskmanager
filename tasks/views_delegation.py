from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.db import transaction

from .models import Employee, Department


# 👥 Список сотрудников
@login_required
def employee_list(request):
    """
    Просмотр всех сотрудников (только для админов)
    """
    employees = Employee.objects.select_related("user", "department").all().order_by("user__last_name")
    return render(request, "tasks/employee_list.html", {"employees": employees})

@login_required
def employee_detail(request, employee_id):
    """
    Карточка сотрудника — доступна всем авторизованным.
    """
    employee = get_object_or_404(Employee.objects.select_related("user", "department"), id=employee_id)

    # Проверяем замещение
    active_delegate = employee.get_active_delegate()
    delegated_from = Employee.objects.filter(delegate_to=employee, delegate_until__gte=timezone.now().date()).first()

    context = {
        "employee": employee,
        "active_delegate": active_delegate,
        "delegated_from": delegated_from,
    }
    return render(request, "tasks/employee_detail.html", context)

# 🚫 Уведомление о заморозке (при активном делегировании)
@login_required
def frozen_notice(request):
    """
    Если пользователь временно передал полномочия — доступ к системе ограничен.
    """
    employee = request.user.employee

    # Если срок замещения истёк, сразу очистим его
    if employee.delegate_until and employee.delegate_until < timezone.now().date():
        employee.delegate_to = None
        employee.delegate_until = None
        employee.save(update_fields=["delegate_to", "delegate_until"])

    return render(request, "tasks/frozen_notice.html", {"employee": employee})


# 🔁 Управление замещением
@login_required
@transaction.atomic
def my_delegation(request):
    """
    Пользователь может передать свои полномочия коллеге в отделе.
    """
    employee = request.user.employee

    # Автоочистка старых замещений
    if employee.delegate_until and employee.delegate_until < timezone.now().date():
        employee.delegate_to = None
        employee.delegate_until = None
        employee.save(update_fields=["delegate_to", "delegate_until"])

    # 👥 Список возможных замещающих — только коллеги из отдела
    colleagues = (
        Employee.objects.filter(department=employee.department)
        .exclude(id=employee.id)
        .select_related("user")
        .order_by("user__last_name")
        if employee.department else Employee.objects.none()
    )

    # Отмена замещения
    if "cancel_delegation" in request.POST:
        employee.delegate_to = None
        employee.delegate_until = None
        employee.save(update_fields=["delegate_to", "delegate_until"])
        messages.success(request, "Вы отменили замещение. Доступ полностью восстановлен.")
        return redirect("my_delegation")

    # Создание нового замещения
    if request.method == "POST" and "delegate_to" in request.POST:
        delegate_to_id = request.POST.get("delegate_to")
        delegate_until = request.POST.get("delegate_until")

        if not delegate_to_id or not delegate_until:
            messages.error(request, "Выберите сотрудника и укажите дату окончания замещения.")
        else:
            try:
                delegate_to = Employee.objects.get(id=delegate_to_id, department=employee.department)
            except Employee.DoesNotExist:
                messages.error(request, "Можно выбрать только коллегу из вашего отдела.")
                return redirect("my_delegation")

            employee.delegate_to = delegate_to
            employee.delegate_until = delegate_until
            employee.save(update_fields=["delegate_to", "delegate_until"])
            messages.success(request, f"Вы передали свои полномочия {delegate_to.user.get_full_name()}.")
            return redirect("my_delegation")

    active_delegate = employee.get_active_delegate()
    delegated_from = Employee.objects.filter(delegate_to=employee, delegate_until__gte=timezone.now().date()).first()

    context = {
        "employee": employee,
        "colleagues": colleagues,
        "active_delegate": active_delegate,  # кого выбрал сам
        "delegated_from": delegated_from,    # кого замещает он
    }

    return render(request, "tasks/my_delegation.html", context)
