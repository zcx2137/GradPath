"""学生应用的Django Admin配置。

此文件用于在Django管理后台中注册和配置学生应用的模型，
以便管理员可以方便地查看和管理相关数据。
"""

from django.contrib import admin
from .models import StudentProfile, Submission, SubmissionCategory


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """学生档案模型的Admin配置。"""
    list_display = ('id', 'user', 'full_name')


@admin.register(SubmissionCategory)
class SubmissionCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'name', 'default_score', 'max_score')
    list_filter = ('group',)  # 按大类筛选


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'category', 'self_rating', 'approved', 'approved_score', 'timestamp')
    list_filter = ('category__group', 'approved')