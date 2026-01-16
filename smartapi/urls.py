from django.urls import path
from . import views

app_name = 'smartapi'

urlpatterns = [
    path('employees/', views.employees_view, name='employees'),
    path('departments/', views.departments_view, name='departments'),
    path('users/', views.users_view, name='users'),
]