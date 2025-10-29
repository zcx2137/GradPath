from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.counselor_register, name='counselor_register'),
    path('login/', views.counselor_login, name='counselor_login'),
    path('logout/', views.counselor_logout, name='counselor_logout'),
    path('students/', views.view_all_students, name='view_all_students'),
    path('dashboard/', views.counselor_dashboard, name='counselor_dashboard'),
    path('review/', views.review_submissions, name='review_submissions'),
    path('rules/', views.counselor_rules, name='counselor_rules'),
    path('approve/<int:submission_id>/', views.approve_submission, name='approve_submission'),
    path('reject/<int:submission_id>/', views.reject_submission, name='reject_submission'),
    path('set-score/<int:student_id>/', views.set_academic_score, name='set_academic_score'),
]