from django.urls import path
from . import views

urlpatterns = [
    path("ask-bot/", views.chatgpt_stream, name="chatgpt_stream"),
    path("ask-bot-smart/", views.chatgpt_context_stream, name="chatgpt_context_stream"),
    path("add-page/", views.add_page, name="add_page"),
]
