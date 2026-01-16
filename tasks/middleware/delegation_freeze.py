from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from ..models import Employee  # путь остаётся тем же

class DelegationFreezeMiddleware:
    """
    Middleware блокирует действия пользователя, если он находится в режиме замещения (в отпуске).
    Разрешает только выход (logout) и страницу уведомления о заморозке.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Пропускаем неавторизованных пользователей
        if not request.user.is_authenticated:
            return self.get_response(request)

        try:
            employee = Employee.objects.get(user=request.user)
        except Employee.DoesNotExist:
            return self.get_response(request)

        # Обработка кнопки "Отменить замещение" на странице my_delegation или frozen_notice
        if request.method == "POST" and "cancel_delegation" in request.POST:
            employee.delegate_to = None
            employee.delegate_until = None
            employee.save()
            messages.success(request, "✅ Замещение отменено. Ваш аккаунт снова активен.")
            return redirect("my_delegation")

        # Проверяем, активен ли режим замещения
        if employee.is_frozen:
            # Проверяем, не истекло ли замещение (чтобы автоматически "разморозить")
            if employee.delegate_until and employee.delegate_until < timezone.now().date():
                employee.delegate_to = None
                employee.save()
                messages.info(request, "⏳ Срок замещения истёк. Ваш аккаунт снова активен.")
                return self.get_response(request)

            # Пути, которые доступны во время заморозки
            allowed_paths = [
                reverse('logout'),
                reverse('frozen_notice'),
                reverse('my_delegation')
            ]

            # Если пользователь пытается перейти куда-то ещё — блокируем
            if not any(request.path.startswith(path) for path in allowed_paths):
                messages.warning(
                    request,
                    "Ваш аккаунт временно заморожен, так как вы передали свои обязанности замещающему сотруднику."
                )
                return redirect('frozen_notice')

        return self.get_response(request)
