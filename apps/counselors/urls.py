from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.counselor_register, name='counselor_register'),
    path('login/', views.counselor_login, name='counselor_login'),
    path('logout/', views.counselor_logout, name='counselor_logout'),
    path('profile/', views.counselor_profile, name='counselor_profile'),
    path('students/', views.view_all_students, name='view_all_students'),
    path('export-students/', views.export_students, name='export_students'),
    path('dashboard/', views.counselor_dashboard, name='counselor_dashboard'),
    path('review/', views.review_submissions, name='review_submissions'),
    path('rules/', views.counselor_rules, name='counselor_rules'),
    path('rules/', views.rules_management, name='rules_management'),
    path('rules/add/', views.add_rule, name='add_rule'),
    path('rules/<str:rule_type>/', views.rule_detail, name='rule_detail'),
    path('rules/edit/<int:rule_id>/', views.edit_rule, name='edit_rule'),
    path('rules/delete/<int:rule_id>/', views.delete_rule, name='delete_rule'),
    path('approve/<int:submission_id>/', views.approve_submission, name='approve_submission'),
    path('reject/<int:submission_id>/', views.reject_submission, name='reject_submission'),
    path('review/<int:submission_id>/', views.review_detail, name='review_detail'),
    path('set-score/<int:student_id>/', views.set_academic_score, name='set_academic_score'),
]