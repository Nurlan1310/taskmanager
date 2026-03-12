from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'tasks', api_views.TaskViewSet, basename='task')
router.register(r'cards', api_views.EventCardViewSet, basename='card')
router.register(r'employees', api_views.EmployeeViewSet, basename='employee')

urlpatterns = [
    path('auth/login/', api_views.login_view, name='api-login'),
    path('auth/logout/', api_views.logout_view, name='api-logout'),
    path('auth/me/', api_views.me_view, name='api-me'),
    path('auth/profile/', api_views.update_profile_view, name='api-update-profile'),
    path('auth/change-password/', api_views.change_password_view, name='api-change-password'),
    path('auth/upload-photo/', api_views.upload_profile_photo_view, name='api-upload-photo'),
    path('auth/csrf/', api_views.csrf_view, name='api-csrf'),
    path('dashboard/', api_views.dashboard_view, name='api-dashboard'),
    path('tasks/<int:task_id>/take/', api_views.take_task_view, name='api-take-task'),
    path('tasks/<int:task_id>/complete/', api_views.complete_task_view, name='api-complete-task'),
    path('tasks/<int:task_id>/execute/', api_views.execute_task_view, name='api-execute-task'),
    path('tasks/<int:task_id>/redirect/', api_views.redirect_task_view, name='api-redirect-task'),
    path('tasks/<int:task_id>/return-redirect/', api_views.return_redirect_task_view, name='api-return-redirect-task'),
    path('categories/', api_views.categories_view, name='api-categories'),
    path('departments/', api_views.departments_view, name='api-departments'),
    path('tasks/<int:task_id>/attachments/', api_views.upload_task_attachment, name='api-upload-attachment'),
    path('tasks/<int:task_id>/approve-plan/', api_views.approve_plan_view, name='api-approve-plan'),
    path('tasks/<int:task_id>/reject-plan/', api_views.reject_plan_view, name='api-reject-plan'),
    path('tasks/<int:task_id>/review/', api_views.task_review_view, name='api-task-review'),
    path('tasks/<int:task_id>/review/approve/', api_views.task_review_approve_view, name='api-task-review-approve'),
    path('tasks/<int:task_id>/review/reject/', api_views.task_review_reject_view, name='api-task-review-reject'),
    path('tasks/<int:task_id>/creation-approval/', api_views.creation_approval_view, name='api-creation-approval'),
    path('tasks/<int:task_id>/approve-creation/', api_views.approve_creation_view, name='api-approve-creation'),
    path('tasks/<int:task_id>/reject-creation/', api_views.reject_creation_view, name='api-reject-creation'),
    path('tasks/<int:task_id>/recall/', api_views.recall_task_view, name='api-recall-task'),
    path('cards/<int:card_id>/approvers/', api_views.card_approvers_view, name='api-card-approvers'),
    path('cards/<int:card_id>/upload-corrected-plan/', api_views.upload_corrected_plan_view, name='api-upload-corrected-plan'),
    path('cards/<int:card_id>/download-plan/', api_views.download_plan_file_view, name='api-download-plan'),
    path('statistics/', api_views.statistics_view, name='api-statistics'),
    # KPI
    path('kpi/reports/generate/', api_views.kpi_generate_report_view, name='api-kpi-generate'),
    path('kpi/results/', api_views.kpi_results_view, name='api-kpi-results'),
    # Уведомления - специфичные маршруты должны идти перед общими
    path('notifications/mark-all-read/', api_views.notifications_mark_all_read_view, name='api-notifications-mark-all-read'),
    path('notifications/delete-read/', api_views.notifications_delete_read_view, name='api-notifications-delete-read'),
    path('notifications/<int:notification_id>/read/', api_views.notification_mark_read_view, name='api-notification-mark-read'),
    path('notifications/', api_views.notifications_list_view, name='api-notifications-list'),
    path('', include(router.urls)),
]

