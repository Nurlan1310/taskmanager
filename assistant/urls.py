# assistant/urls.py

from django.urls import path
from .views import AssistantQueryApi

urlpatterns = [
    path("ask/", AssistantQueryApi.as_view()),
]
