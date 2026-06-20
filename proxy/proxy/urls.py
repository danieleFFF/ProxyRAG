from django.urls import path
from .views import getModels, chat

urlpatterns = [
    path("models", getModels.as_view()),
    path("chat/completions", chat.as_view()),
]
