from django.urls import path
from . import api_views_mob  # Твой файл API для мобилки

urlpatterns = [
    # =======================================
    # 🌍 WEB (Сайт) - ЗАКОММЕНТИРОВАНО
    # =======================================
    # Оставляем выключенными, чтобы работал React-фронтенд друга.
    
    # path('', views_tasks.task_list, name='task_list'),

    # =======================================
    # 📱 API (Мобильное приложение)
    # =======================================

    # Авторизация
    path("login/", api_views_mob.LoginApi.as_view()),
    
    # Задачи (основной список, поручения, отдел)
    path("my-tasks/", api_views_mob.MyTasksApi.as_view()),
    
    # 🔥 НОВОЕ: Фильтры для руководителей (отделы, карточки, сотрудники)
    path("filters/", api_views_mob.FiltersApi.as_view()),
    
    # Детали задачи и действия
    path("task/<int:task_id>/", api_views_mob.TaskDetailApi.as_view()),
    path("task/<int:task_id>/comments/", api_views_mob.TaskCommentsApi.as_view()),
    path("task/<int:task_id>/attachment/", api_views_mob.TaskAttachmentUploadApi.as_view()),

    # Уведомления (колокольчик)
    path("notifications/", api_views_mob.NotificationListApi.as_view()),
    path("notifications/<int:notification_id>/read/", api_views_mob.NotificationMarkReadApi.as_view()),
    path("notifications/mark-all/", api_views_mob.NotificationMarkAllReadApi.as_view()),

    # Push-уведомления (FCM)
    path("register-fcm/", api_views_mob.FCMRegisterApi.as_view()),
    path("unregister-fcm/", api_views_mob.FCMUnregisterApi.as_view()),
]