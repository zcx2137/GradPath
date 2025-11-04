from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from students.models import StudentProfile
from counselors.models import CounselorProfile
from django import forms
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse


# 仅允许超级管理员访问
def is_superadmin(user):
    return user.is_authenticated and user.is_superuser


# 用户添加表单
class UserCreationForm(forms.Form):
    user_type = forms.ChoiceField(choices=[('student', '学生'), ('counselor', '辅导员')])
    username = forms.CharField(max_length=150)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)
    full_name = forms.CharField(max_length=100)

    # 学生特有字段
    student_id = forms.CharField(max_length=20, required=False)
    college = forms.CharField(max_length=100, required=False)

    # 辅导员特有字段
    employee_id = forms.CharField(max_length=20, required=False)

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('用户名已存在')
        return username

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password1') != cleaned_data.get('password2'):
            self.add_error('password2', '两次密码不一致')

        user_type = cleaned_data.get('user_type')
        if user_type == 'student' and not cleaned_data.get('student_id'):
            self.add_error('student_id', '学生必须填写学号')
        if user_type == 'counselor' and not cleaned_data.get('employee_id'):
            self.add_error('employee_id', '辅导员必须填写工号')


# 管理员 dashboard
@user_passes_test(is_superadmin, login_url='admin_login')
def admin_dashboard(request):
    students = StudentProfile.objects.select_related('user').all()
    counselors = CounselorProfile.objects.select_related('user').all()

    return render(request, 'admins/dashboard.html', {
        'students': students,
        'counselors': counselors,
    })


# 管理员登录视图
def admin_login(request):
    # 如果用户已登录且是超级管理员，直接跳转到管理面板
    if request.user.is_authenticated and is_superadmin(request.user):
        return redirect('admin_dashboard')

    error_message = ""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if is_superadmin(user):  # 验证是否为超级管理员
                login(request, user)
                # 登录成功后跳转到之前尝试访问的页面（通过next参数）
                next_page = request.GET.get('next', 'admin_dashboard')
                return redirect(next_page)
            else:
                error_message = "您没有管理员权限"
        else:
            error_message = "用户名或密码错误"

    return render(request, 'admins/admin_login.html', {'error_message': error_message})


# 管理员登出视图
@user_passes_test(is_superadmin)
def admin_logout(request):
    logout(request)
    return redirect('admin_login')  # 登出后返回管理员登录页


# 添加用户
@user_passes_test(is_superadmin, login_url='admin_login')
def add_user(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            # 创建用户
            user = User.objects.create_user(
                username=data['username'],
                password=data['password1']
            )

            # 创建对应角色的档案
            if data['user_type'] == 'student':
                StudentProfile.objects.create(
                    user=user,
                    student_id=data['student_id'],
                    full_name=data['full_name'],
                    college=data.get('college', '')
                )
            else:
                CounselorProfile.objects.create(
                    user=user,
                    employee_id=data['employee_id'],
                    full_name=data['full_name'],
                    college=data.get('college', '')
                )

            messages.success(request, f'{data["user_type"]}账号创建成功')
            return redirect('admin_dashboard')
    else:
        form = UserCreationForm()

    return render(request, 'admins/add_user.html', {'form': form})


# 删除用户
@user_passes_test(is_superadmin, login_url='admin_login')
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    # 检查用户类型并删除关联档案
    if hasattr(user, 'profile'):
        user.profile.delete()
    if hasattr(user, 'counselor_profile'):
        user.counselor_profile.delete()
    user.delete()
    messages.success(request, '用户已删除')
    return redirect('admin_dashboard')