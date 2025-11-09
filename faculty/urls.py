from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.faculty_login, name='faculty_login'),
    path('logout/', views.faculty_logout, name='faculty_logout'),
    path('dashboard/', views.faculty_dashboard, name='faculty_dashboard'),
    path('profile/', views.faculty_profile, name='faculty_profile'),
    path('change-password/', views.faculty_change_password, name='faculty_change_password'),
    path('analytics/', views.faculty_analytics, name='faculty_analytics'),
    path('club/<int:club_id>/', views.club_detail, name='club_detail'),
    path('club/<int:club_id>/analytics/', views.club_analytics_faculty, name='club_analytics_faculty'),
    path('club/<int:club_id>/appoint-head/', views.appoint_club_head, name='appoint_club_head'),
    path('club/<int:club_id>/add-member/', views.add_club_member, name='add_club_member'),
    path('club/<int:club_id>/remove-member/<int:member_id>/', views.remove_club_member, name='remove_club_member'),
]