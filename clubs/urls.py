from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.club_login, name='club_login'),
    path('logout/', views.club_logout, name='club_logout'),
    path('dashboard/', views.club_dashboard, name='club_dashboard'),
    path('profile/', views.club_member_profile, name='club_member_profile'),
    path('change-password/', views.club_member_change_password, name='club_member_change_password'),
    path('analytics/', views.club_analytics, name='club_analytics'),
    path('event/create/', views.create_event, name='create_event'),
    path('event/<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('event/<int:event_id>/delete/', views.delete_event, name='delete_event'),
    path('event/<int:event_id>/start/', views.start_event, name='start_event'),
    path('event/<int:event_id>/end/', views.end_event, name='end_event'),
    path('event/<int:event_id>/attendance/', views.event_attendance, name='event_attendance'),
    path('event/<int:event_id>/download-report/', views.download_event_report, name='download_event_report'),
]