"""学生应用的URL配置。

此文件定义了学生应用的所有URL路由。
"""

from django.urls import path
from . import views

# URL模式列表
urlpatterns = [
    # 主页
    path('', views.index, name='index'),
    # 用户注册
    path('register/', views.register, name='register'),
    # 用户登录
    path('login/', views.login_view, name='login'),
    # 用户注销
    path('logout/', views.logout_view, name='logout'),
    # 个人资料页
    path('profile/', views.profile, name='profile'),
    # 上传资料页
    path('upload/', views.upload, name='upload'),
    # 状态查看页
    path('submissions/', views.submissions, name='submissions'),
    path('submissions/delete/<int:submission_id>/', views.delete_submission, name='delete_submission'),
    # 加分细则
    path('rules/', views.rules, name='rules'),
]