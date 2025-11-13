from django.urls import path
from . import views
from . import views_cards
from . import views_tasks
from . import views_delegation

urlpatterns = [
    path('', views_tasks.task_list, name='task_list'),
    path('employees/', views_delegation.employee_list, name='employee_list'),
    path('employees/<int:employee_id>/', views_delegation.employee_detail, name='employee_detail'),

    # --- Задачи ---
    path("task/<int:task_id>/", views_tasks.task_detail, name="task_detail"),
    path("tasks/<int:task_id>/take/", views_tasks.take_task, name="take_task"),
    path("tasks/<int:task_id>/delegate/", views_tasks.delegate_task, name="delegate_task"),
    # path('tasks/create/', views_tasks.create_task, name='create_task'),
    path('tasks/<int:task_id>/complete/', views_tasks.complete_task, name='complete_task'),
    path("tasks/<int:task_id>/execute/", views_tasks.task_execute, name="task_execute"),

    # --- Карточки ---
    path("card/<int:card_id>/", views_cards.card_detail, name="card_detail"),
    path("card/<int:card_id>/plan/review/", views_cards.plan_review, name="plan_review"),
    path("cards/create/", views_cards.card_create, name="card_create"),
    path('card/<int:card_id>/task/create/', views_tasks.task_create_for_card, name='task_create_for_card'),

    # --- Делегирование ---
    path("delegation/", views_delegation.my_delegation, name="my_delegation"),
    path('frozen/', views_delegation.frozen_notice, name='frozen_notice'),

    # --- Согласование планов ---
    path("tasks/approve/<int:task_id>/", views_tasks.approve_plan, name="approve_plan"),
    path("tasks/reject/<int:task_id>/", views_tasks.reject_plan, name="reject_plan"),

    # --- Проверка выполнения задач ---
    path("tasks/<int:task_id>/review/", views_tasks.task_review, name="task_review"),
    path("tasks/<int:task_id>/review/take/", views_tasks.task_review_take, name="task_review_take"),
    path("tasks/<int:task_id>/review/approve/", views_tasks.task_review_approve, name="task_review_approve"),
    path("tasks/<int:task_id>/review/reject/", views_tasks.task_review_reject, name="task_review_reject"),

    path("notifications/", views_tasks.notifications_list, name="notifications"),
    path("notifications/read/<int:note_id>/", views_tasks.notification_read, name="notification_read"),
    path("notifications/read_all/", views_tasks.notifications_read_all, name="notifications_read_all"),

]
