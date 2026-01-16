# tasks/decorators.py
from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

def role_required(*roles):
    """
    Проверяет, что у пользователя есть Employee и его роль входит в разрешённые.
    Пример:
        @role_required("director", "deputy")
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            emp = getattr(request.user, "employee", None)
            if not emp or emp.role not in roles:
                messages.error(request, "Недостаточно прав для выполнения этого действия.")
                return redirect("task_list")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
