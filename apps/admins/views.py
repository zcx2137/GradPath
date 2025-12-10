from django.db import models
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
    grade = forms.CharField(max_length=20, required=False, label="负责年级")

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
        if user_type == 'counselor' and not cleaned_data.get('grade'):
            self.add_error('grade', '辅导员必须填写负责年级')


# 编辑用户表单
class UserEditForm(forms.Form):
    full_name = forms.CharField(max_length=100)
    college = forms.ChoiceField(
        choices=[
            ('info', '信息学院'),
            ('other', '其他'),
        ],
        label="学院"
    )
    grade = forms.CharField(max_length=20, label="年级")  # 通用年级字段（学生和辅导员共用）

    # 学生特有字段（学号即用户名）
    student_id = forms.CharField(max_length=20, required=False, label="学号（用户名）")

    # 辅导员特有字段（工号即用户名）
    employee_id = forms.CharField(max_length=20, required=False, label="工号（用户名）")

    def __init__(self, *args, **kwargs):
        # 接收当前用户ID，用于校验时排除自身
        self.user_id = kwargs.pop('user_id', None)
        super().__init__(*args, **kwargs)

    def clean_student_id(self):
        # 校验学生学号（用户名）的唯一性
        student_id = self.cleaned_data.get('student_id')
        if not student_id:
            return student_id

        # 检查是否有其他用户的username或学生的student_id占用该值
        if User.objects.exclude(id=self.user_id).filter(username=student_id).exists():
            raise forms.ValidationError("该学号已被用作登录用户名，请更换")
        if StudentProfile.objects.exclude(user_id=self.user_id).filter(student_id=student_id).exists():
            raise forms.ValidationError("该学号已被其他学生使用，请更换")
        return student_id

    def clean_employee_id(self):
        # 校验辅导员工号（用户名）的唯一性
        employee_id = self.cleaned_data.get('employee_id')
        if not employee_id:
            return employee_id

        # 检查是否有其他用户的username或辅导员的employee_id占用该值
        if User.objects.exclude(id=self.user_id).filter(username=employee_id).exists():
            raise forms.ValidationError("该工号已被用作登录用户名，请更换")
        if CounselorProfile.objects.exclude(user_id=self.user_id).filter(employee_id=employee_id).exists():
            raise forms.ValidationError("该工号已被其他辅导员使用，请更换")
        return employee_id


# 重置密码表单
class PasswordResetForm(forms.Form):
    password1 = forms.CharField(widget=forms.PasswordInput, label='新密码')
    password2 = forms.CharField(widget=forms.PasswordInput, label='确认新密码')

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password1') != cleaned_data.get('password2'):
            self.add_error('password2', '两次密码不一致')


# 管理员 dashboard
@user_passes_test(is_superadmin, login_url='admin_login')
def admin_dashboard(request):
    # 1. 获取筛选和独立搜索参数
    filter_college = request.GET.get('college', '')
    filter_grade = request.GET.get('grade', '')
    # 学生专用搜索参数
    student_search = request.GET.get('student_search', '').strip()
    # 辅导员专用搜索参数
    counselor_search = request.GET.get('counselor_search', '').strip()

    # 2. 学生筛选（仅受 student_search 影响）
    students_query = StudentProfile.objects.select_related('user').all()
    if filter_college:
        students_query = students_query.filter(college=filter_college)
    if filter_grade:
        students_query = students_query.filter(grade=filter_grade)
    # 仅使用学生搜索关键词
    if student_search:
        students_query = students_query.filter(
            models.Q(full_name__icontains=student_search) |
            models.Q(student_id__icontains=student_search)
        )
    students = students_query

    # 3. 辅导员筛选（仅受 counselor_search 影响）
    counselors_query = CounselorProfile.objects.select_related('user').all()
    if filter_college:
        counselors_query = counselors_query.filter(college=filter_college)
    if filter_grade:
        counselors_query = counselors_query.filter(grade=filter_grade)
    # 仅使用辅导员搜索关键词
    if counselor_search:
        counselors_query = counselors_query.filter(
            models.Q(full_name__icontains=counselor_search) |
            models.Q(employee_id__icontains=counselor_search)
        )
    counselors = counselors_query

    # 4. 下拉框选项（保持不变）
    college_choices = UserEditForm().fields['college'].choices
    student_grades = set(StudentProfile.objects.values_list('grade', flat=True))
    counselor_grades = set(CounselorProfile.objects.values_list('grade', flat=True))
    all_grades = student_grades.union(counselor_grades)
    grade_choices = sorted([grade for grade in all_grades if grade])

    return render(request, 'admins/dashboard.html', {
        'students': students,
        'counselors': counselors,
        'college_choices': college_choices,
        'grade_choices': grade_choices,
        'current_college': filter_college,
        'current_grade': filter_grade,
        # 传递独立的搜索关键词用于回显
        'student_search': student_search,
        'counselor_search': counselor_search,
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
                    college=data.get('college', ''),
                    grade=data['grade']
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


# 编辑用户
@user_passes_test(is_superadmin, login_url='admin_login')
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    is_student = hasattr(user, 'profile')  # 假设学生关联表为profile
    is_counselor = hasattr(user, 'counselor_profile')  # 假设辅导员关联表为counselor_profile

    if not is_student and not is_counselor:
        messages.error(request, '无效的用户类型')
        return redirect('admin_dashboard')

    # 初始化表单数据（包含当前用户ID用于校验）
    initial_data = {}
    if is_student:
        initial_data = {
            'full_name': user.profile.full_name,
            'student_id': user.profile.student_id,  # 学号初始值=当前用户名
            'college': user.profile.college,
            'grade': user.profile.grade  # 学生年级初始值
        }
    elif is_counselor:
        initial_data = {
            'full_name': user.counselor_profile.full_name,
            'employee_id': user.counselor_profile.employee_id,  # 工号初始值=当前用户名
            'college': user.counselor_profile.college,
            'grade': user.counselor_profile.grade
        }

    if request.method == 'POST':
        form = UserEditForm(request.POST, user_id=user.id)  # 传入当前用户ID
        if form.is_valid():
            data = form.cleaned_data

            if is_student:
                # 学生：同步学号和用户名
                new_student_id = data['student_id']
                user.username = new_student_id  # 用户名=新学号
                user.save()
                user.profile.full_name = data['full_name']
                user.profile.student_id = new_student_id
                user.profile.college = data['college']
                user.profile.grade = data['grade']
                user.profile.save()
                messages.success(request, '学生信息已更新')

            elif is_counselor:
                # 辅导员：同步工号和用户名
                new_employee_id = data['employee_id']
                user.username = new_employee_id  # 用户名=新工号
                user.save()
                user.counselor_profile.full_name = data['full_name']
                user.counselor_profile.employee_id = new_employee_id
                user.counselor_profile.college = data['college']
                user.counselor_profile.grade = data['grade']
                user.counselor_profile.save()
                messages.success(request, '辅导员信息已更新')

            return redirect('admin_dashboard')
    else:
        form = UserEditForm(initial=initial_data, user_id=user.id)  # 传入当前用户ID

    return render(request, 'admins/edit_user.html', {
        'form': form,
        'user': user,
        'is_student': is_student,
        'is_counselor': is_counselor  # 新增辅导员标识，用于模板提示
    })


# 重置用户密码
@user_passes_test(is_superadmin, login_url='admin_login')
def reset_password(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['password1'])
            user.save()
            messages.success(request, '密码已重置')
            return redirect('admin_dashboard')
    else:
        form = PasswordResetForm()

    return render(request, 'admins/reset_password.html', {
        'form': form,
        'user': user
    })