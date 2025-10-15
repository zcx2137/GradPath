from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import StudentProfile, Submission
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.forms import ModelForm
from django.contrib.auth import authenticate
from django import forms
from django.contrib.auth.models import User
from django.contrib import messages


# 学生注册表单
class StudentRegistrationForm(forms.Form):
    student_id = forms.CharField(label='学号', max_length=20)
    password1 = forms.CharField(label='密码', widget=forms.PasswordInput)
    password2 = forms.CharField(label='确认密码', widget=forms.PasswordInput)
    full_name = forms.CharField(label='姓名', max_length=100, required=False)

    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id')
        if StudentProfile.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError('该学号已被注册')
        return student_id

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', '两次密码输入不一致')
        return cleaned_data


# 学生档案表单
class ProfileForm(ModelForm):

    class Meta:
        model = StudentProfile
        fields = [
            'full_name', 'student_id', 'grade', 'college',
            'department', 'major', 'enrollment_year',

            'gender', 'ethnicity', 'political_status', 'id_card',

            'phone', 'email'
        ]


# 学生提交表单
class SubmissionForm(ModelForm):
    class Meta:
        model = Submission
        fields = ['category', 'remarks', 'file', 'self_rating']
        widgets = {
            'remarks': forms.Textarea(attrs={'rows': 3, 'placeholder': '请填写相关说明或证明信息'}),
            'self_rating': forms.NumberInput(attrs={'min': 0, 'step': 0.5, 'placeholder': '请填写自评分数'}),
        }
        labels = {
            'category': '加分项类型',
            'remarks': '备注说明',
            'self_rating': '自评加分',
        }


# 用户注册
def register(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            # 创建用户（使用学号作为用户名）
            student_id = form.cleaned_data['student_id']
            user = User.objects.create_user(
                username=student_id,  # 用学号作为用户名
                password=form.cleaned_data['password1']
            )
            # 创建学生档案
            StudentProfile.objects.create(
                user=user,
                student_id=student_id,
                full_name=form.cleaned_data.get('full_name', '')
            )
            return redirect('login')
    else:
        form = StudentRegistrationForm()
    return render(request, 'students/register.html', {'form': form})


# 用户登录
def login_view(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        password = request.POST.get('password')

        # 验证表单数据
        if not student_id or not password:
            return render(request, 'students/login.html', {
                'error': '请输入学号和密码',
            })

        # 使用学号（即用户名）验证
        user = authenticate(username=student_id, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('index')  # 登录后跳转到主页
        else:
            return render(request, 'students/login.html', {
                'error': '学号或密码不正确',
            })
    return render(request, 'students/login.html')


# 用户登出
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def index(request):
    # 应用主页视图
    return render(request, 'students/home.html')


@login_required
def profile(request):
    # 获取当前登录用户的 Profile，如不存在则报404
    try:
        profile = request.user.profile
    except StudentProfile.DoesNotExist:
        raise Http404("未找到用户个人资料。")

    if request.method == 'POST':
        # 使用POST数据和已存在的profile实例来创建表单
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            # 保存成功后重定向回个人资料页，以显示更新后的信息
            return redirect('profile')
    else:
        # GET请求时，使用已存在的profile实例创建表单
        form = ProfileForm(instance=profile)

    return render(request, 'students/profile.html', {'form': form})


@login_required
def upload(request):
    """处理文件上传请求。
    """
    # 获取当前用户的Profile，后续用于关联Submission
    profile = request.user.profile
    if request.method == 'POST':
        # POST请求时，使用POST数据和上传的文件来创建表单
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            # 暂不提交到数据库，以便修改student字段
            new_sub = form.save(commit=False)
            # 将提交记录与当前学生关联
            new_sub.student = profile
            # 保存到数据库
            new_sub.save()
            # 成功后重定向到提交记录列表页面
            return redirect('submissions')
    else:
        # GET请求时，创建一个空的表单实例
        form = SubmissionForm()
    return render(request, 'students/upload.html', {'form': form})


@login_required
def submissions(request):
    profile = request.user.profile
    # 获取当前用户所有提交，按时间倒序排列
    subs = Submission.objects.filter(student=profile).order_by('-timestamp')
    return render(request, 'students/submissions.html', {'submissions': subs})


def delete_submission(request, submission_id):
    # 获取要删除的提交记录，确保属于当前用户
    submission = get_object_or_404(Submission, id=submission_id)

    # 验证权限：只有提交者本人才能删除
    if submission.student.user != request.user:
        messages.error(request, "你没有权限删除此提交记录")
        return redirect('submissions')

    # 执行删除操作
    if request.method == 'POST':
        submission.delete()
        messages.success(request, "提交记录已成功删除")
        return redirect('submissions')

    # 如果是GET请求，返回确认页面
    return render(request, 'students/confirm_delete.html', {'submission': submission})


def rules(request):
    return render(request, 'students/rules.html')


def root_view(request):
    # 根路径视图，显示登录选择页面
    return render(request, 'index.html')