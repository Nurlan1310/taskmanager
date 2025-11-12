# tasks/views/delegation.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone

from tasks.models import Employee

@login_required
def my_delegation(request):
    employee = Employee.objects.get(user=request.user)
    employees = Employee.objects.exclude(id=employee.id)

    if request.method == "POST":
        delegate_to_id = request.POST.get("delegate_to")
        delegate_until = request.POST.get("delegate_until")

        if not delegate_to_id or not delegate_until:
            messages.error(request, "Выберите замещающего и укажите дату окончания замещения.")
        else:
            delegate_to = Employee.objects.get(id=delegate_to_id)
            employee.delegate_to = delegate_to
            employee.delegate_until = delegate_until
            employee.save()
            messages.success(request, f"Вы успешно передали свои полномочия {delegate_to}.")
            return redirect("my_delegation")

    # Проверяем, активно ли замещение сейчас
    active_delegate = employee.get_active_delegate()
    context = {
        "employee": employee,
        "employees": employees,
        "active_delegate": active_delegate,
    }
    if request.GET.get("cancel"):
        employee.delegate_to = None
        employee.delegate_until = None
        employee.save()
        messages.info(request, "Замещение отменено.")
        return redirect("my_delegation")

    return render(request, "tasks/my_delegation.html", context)
