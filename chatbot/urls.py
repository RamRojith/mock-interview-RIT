from django.urls import path

from . import views


app_name = "chatbot"

urlpatterns = [
    path("api/chat/", views.chat, name="chat"),
    path("api/history/", views.history, name="history"),
    path("api/questions/", views.questions, name="questions"),
]
