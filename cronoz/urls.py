from django.urls import path
from . import views

app_name = 'cronoz'

urlpatterns = [
    # AI Chat Interface
    path('chat/', views.ai_chat_interface, name='chat_interface'),

    # Student AI Endpoints
    path('api/student/suggestions/', views.student_ai_suggestions, name='student_suggestions'),
    path('api/student/chat/', views.student_ai_chat, name='student_chat'),

    # Club Member AI Endpoints
    path('api/club/suggestions/', views.club_ai_suggestions, name='club_suggestions'),
    path('api/club/chat/', views.club_ai_chat, name='club_chat'),

    # Faculty AI Endpoints
    path('api/faculty/suggestions/', views.faculty_ai_suggestions, name='faculty_suggestions'),
    path('api/faculty/chat/', views.faculty_ai_chat, name='faculty_chat'),
]