from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.counselor_register, name='counselor_register'),
    path('login/', views.counselor_login, name='counselor_login'),
    path('dashboard/', views.counselor_dashboard, name='counselor_dashboard'),
    path('review/', views.review_submissions, name='review_submissions'),
    path('approve/<int:submission_id>/', views.approve_submission, name='approve_submission'),
    path('students/', views.view_all_students, name='view_all_students'),
]