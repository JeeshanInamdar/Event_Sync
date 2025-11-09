from django.urls import path
from . import views

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('<int:event_id>/', views.event_detail, name='event_detail'),
    path('<int:event_id>/register/', views.event_register, name='event_register'),
    path('<int:event_id>/cancel/', views.event_cancel_registration, name='event_cancel_registration'),
    path('my-registrations/', views.my_registrations, name='my_registrations'),
    path('my-attendance/', views.my_attendance, name='my_attendance'),
]