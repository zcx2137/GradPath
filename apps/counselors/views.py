# app/counselors/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from .models import CounselorProfile
from django import forms
from django.contrib.auth.decorators import login_required
from students.models import StudentProfile, Submission

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


@login_required
def counselor_dashboard(request):
    """辅导员控制面板，显示待审核材料数量等统计信息"""
    # 验证是否为辅导员
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')  # 非辅导员跳转到学生登录

    pending_count = Submission.objects.filter(approved=False).count()
    total_students = StudentProfile.objects.count()
    return render(request, 'counselors/dashboard.html', {
        'pending_count': pending_count,
        'total_students': total_students
    })


@login_required
def review_submissions(request):
    """查看所有待审核的学生材料"""
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    submissions = Submission.objects.filter(approved=False).order_by('-timestamp')
    return render(request, 'counselors/review_submissions.html', {
        'submissions': submissions
    })

@login_required
def approve_submission(request, submission_id):
    """审核通过学生提交的材料"""
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    submission = get_object_or_404(Submission, id=submission_id)
    submission.approved = True
    submission.save()
    return redirect('review_submissions')


@login_required
def view_all_students(request):
    """查看所有学生信息"""
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    students = StudentProfile.objects.all().select_related('user')
    return render(request, 'counselors/all_students.html', {
        'students': students
    })