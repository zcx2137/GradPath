# app/counselors/views.py
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from .models import CounselorProfile
from django import forms
from django.contrib.auth.decorators import login_required
from students.models import StudentProfile, Submission
from django.contrib.auth import logout
from decimal import Decimal, InvalidOperation

# 辅导员注册表单
class CounselorRegistrationForm(forms.Form):
    employee_id = forms.CharField(label='工号', max_length=20)
    full_name = forms.CharField(label='姓名', max_length=100)
    college = forms.CharField(label='所属学院', max_length=100)
    password1 = forms.CharField(label='密码', widget=forms.PasswordInput)
    password2 = forms.CharField(label='确认密码', widget=forms.PasswordInput)

    def clean_employee_id(self):
        emp_id = self.cleaned_data.get('employee_id')
        if CounselorProfile.objects.filter(employee_id=emp_id).exists():
            raise forms.ValidationError('该工号已注册')
        return emp_id

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password1') != cleaned_data.get('password2'):
            self.add_error('password2', '两次密码不一致')


# 辅导员注册
def counselor_register(request):
    if request.method == 'POST':
        form = CounselorRegistrationForm(request.POST)
        if form.is_valid():
            emp_id = form.cleaned_data['employee_id']
            user = User.objects.create_user(
                username=emp_id,  # 用工号作为用户名
                password=form.cleaned_data['password1']
            )
            CounselorProfile.objects.create(
                user=user,
                employee_id=emp_id,
                full_name=form.cleaned_data['full_name'],
                college=form.cleaned_data['college']
            )
            return redirect('counselor_login')
    else:
        form = CounselorRegistrationForm()
    return render(request, 'counselors/register.html', {'form': form})


# 辅导员登录
def counselor_login(request):
    if request.method == 'POST':
        emp_id = request.POST.get('employee_id')
        password = request.POST.get('password')
        user = authenticate(username=emp_id, password=password)
        # 验证是否为辅导员账号
        if user and hasattr(user, 'counselor_profile'):
            login(request, user)
            return redirect('counselor_dashboard')
        else:
            return render(request, 'counselors/login.html', {'error': '工号或密码错误'})
    return render(request, 'counselors/login.html')


# 辅导员退出登录
@login_required
def counselor_logout(request):
    # 验证是否为辅导员
    if hasattr(request.user, 'counselor_profile'):
        logout(request)
    return redirect('index')  # 退出后返回登录选择页


# 辅导员控制面板
@login_required
def counselor_dashboard(request):
    # 验证是否为辅导员
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')  # 非辅导员跳转到学生登录

    pending_count = Submission.objects.filter(approved=False).count()
    total_students = StudentProfile.objects.count()
    return render(request, 'counselors/dashboard.html', {
        'pending_count': pending_count,
        'total_students': total_students
    })


# 审核材料
@login_required
def review_submissions(request):
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    submissions = Submission.objects.filter(approved=False).order_by('-timestamp')
    return render(request, 'counselors/review_submissions.html', {
        'submissions': submissions
    })


# 审核通过
@login_required
def approve_submission(request, submission_id):
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    submission = get_object_or_404(Submission, id=submission_id)
    if request.method == 'POST':
        submission.approved = True
        submission.approved_score = request.POST.get('approved_score')
        submission.save()

        # 根据材料类型更新对应成绩
        student = submission.student
        score = Decimal(submission.approved_score or 0)

        # 学术类材料计入学术专长成绩
        academic_categories = ['thesis', 'competition', 'research', 'other_academic']
        # 综合类材料计入综合表现成绩
        comprehensive_categories = ['volunteer', 'leadership', 'social_practice', 'other_comprehensive']

        if submission.category in academic_categories:
            student.academic_expertise_score += score
        elif submission.category in comprehensive_categories:
            student.comprehensive_performance_score += score

        student.save()  # 自动更新总成绩
    return redirect('review_submissions')


# 审核不通过，驳回材料
@login_required
def reject_submission(request, submission_id):
    # 验证是否为辅导员
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    submission = get_object_or_404(Submission, id=submission_id)
    if request.method == 'POST':
        submission.approved = False  # 确保未通过
        submission.rejected = True   # 标记为已驳回
        submission.reject_reason = request.POST.get('reject_reason')  # 获取驳回理由
        submission.save()
    return redirect('review_submissions')


# 查看学生信息
@login_required
def view_all_students(request):
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    students = StudentProfile.objects.all().select_related('user')
    return render(request, 'counselors/all_students.html', {
        'students': students
    })


@login_required
def set_academic_score(request, student_id):
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    student = get_object_or_404(StudentProfile, id=student_id)

    if request.method == 'POST':
        # 仅处理学业综合成绩
        score_str = request.POST.get('academic_comprehensive_score', '').strip()
        if score_str:
            try:
                academic_score = Decimal(score_str)
                student.academic_comprehensive_score = academic_score
                student.save()  # 自动触发总成绩计算
                messages.success(request, "学业综合成绩设置成功")
            except InvalidOperation:
                messages.error(request, "请输入有效的数字")
        return redirect('view_all_students')

    return render(request, 'counselors/set_academic_score.html', {
        'student': student
    })


# 辅导员加分规则管理页面
@login_required
def counselor_rules(request):
    # 验证是否为辅导员身份
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')
    return render(request, 'counselors/rules.html')  # 渲染规则页面模板

