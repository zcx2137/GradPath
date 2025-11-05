# app/counselors/views.py
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from .models import CounselorProfile
from django import forms
from django.contrib.auth.decorators import login_required
from students.models import StudentProfile, Submission, Rule, Notification
from django.contrib.auth import logout
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from datetime import timedelta
from .forms import RuleForm
from django.urls import reverse

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

    # 获取待审核申请
    latest_pending_submissions = Submission.objects.filter(
        approved=False,
        rejected=False
    ).select_related('student').order_by('-timestamp')[:5]
    pending_count = Submission.objects.filter(approved=False, rejected=False).count()

    # 计算本周处理数
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    handled_this_week = Submission.objects.filter(
        approved=True,
        timestamp__date__gte=start_of_week
    ).count()

    # 计算当前生效的加分规则总数
    rules_count = Rule.objects.count()

    total_students = StudentProfile.objects.count()
    return render(request, 'counselors/dashboard.html', {
        'pending_count': pending_count,
        'total_students': total_students,
        'latest_pending_submissions': latest_pending_submissions,
        'rules_count': rules_count,  # 传递规则数量到模板
        'handled_this_week': handled_this_week  # 传递周处理数到模板
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

        # 根据材料类型更新对应成绩（原有逻辑）
        student = submission.student
        score = Decimal(submission.approved_score or 0)
        academic_categories = ['thesis', 'competition', 'research', 'other_academic']
        comprehensive_categories = ['volunteer', 'leadership', 'social_practice', 'other_comprehensive']

        if submission.category in academic_categories:
            student.academic_expertise_score += score
        elif submission.category in comprehensive_categories:
            student.comprehensive_performance_score += score
        student.save()

        # 创建"审核通过"通知
        Notification.objects.create(
            recipient=student.user,  # 接收通知的学生用户
            title="材料审核通过",
            content=f"您提交的「{submission.get_category_display()}」材料已审核通过，核定加分：{submission.approved_score}分",
            type='submission'  # 提交审核类型通知
        )

    return redirect('review_submissions')


# 审核不通过，驳回材料
@login_required
def reject_submission(request, submission_id):
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    submission = get_object_or_404(Submission, id=submission_id)
    if request.method == 'POST':
        submission.approved = False
        submission.rejected = True
        submission.reject_reason = request.POST.get('reject_reason')
        submission.save()

        # 创建"审核驳回"通知
        Notification.objects.create(
            recipient=submission.student.user,  # 接收通知的学生用户
            title="材料审核未通过",
            content=f"您提交的「{submission.get_category_display()}」材料未通过审核，原因：{submission.reject_reason}",
            type='submission'  # 提交审核类型通知
        )

    return redirect('review_submissions')


# 审核详情页
@login_required
def review_detail(request, submission_id):
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    submission = get_object_or_404(Submission, id=submission_id)
    return render(request, 'counselors/review_detail.html', {
        'submission': submission
    })


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
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    # 获取所有规则并按类型分类
    rules = Rule.objects.all()
    context = {
        'student_competition_rules': rules.filter(rule_type='student-competition'),
        'research_achievement_rules': rules.filter(rule_type='research-achievement'),
        'innovation_entrepreneurship_rules': rules.filter(rule_type='innovation-entrepreneurship'),
        'comprehensive_performance_rules': rules.filter(rule_type='comprehensive-performance'),
    }
    return render(request, 'counselors/rules.html', context)


@login_required
def add_rule(request):
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    if request.method == 'POST':
        rule_type = request.POST.get('rule_type')
        rule_desc = request.POST.get('rule_desc')
        rule_item = request.POST.get('item_name')

        if not rule_type or not rule_desc:
            messages.error(request, "请填写所有必填字段")
            return render(request, 'counselors/add_newrules.html')

        # 保存新规则
        new_rule = Rule.objects.create(
            rule_type=rule_type,
            description=rule_desc,
            item_name=rule_item
        )

        # 创建规则上线通知（发送给所有学生）
        students = User.objects.filter(profile__isnull=False)  # 获取所有有学生档案的用户
        for student in students:
            Notification.objects.create(
                recipient=student,
                title="新规则上线",
                content=f"新增「{new_rule.get_rule_type_display()}」类规则：{new_rule.item_name}。详情请查看规则说明。",
                type='rule'  # 规则变动类型通知
            )

        messages.success(request, "加分规则添加成功")
        return redirect('counselor_rules')

    return render(request, 'counselors/add_newrules.html')


# views.py
def rule_detail(request, rule_type):
    # 根据rule_type查询对应规则
    rule_map = {
        'student-competition': '学业竞赛',
        'research-achievement': '科研成果',
        'innovation-entrepreneurship': '创新创业训练',
        'comprehensive-performance': '综合表现加分'
    }

    rules = Rule.objects.filter(rule_type=rule_type)
    return render(request, 'counselors/rule_detail.html', {
        'rules': rules,
        'category_name': rule_map.get(rule_type, '规则详情'),
        'rule_type': rule_type
    })


# 编辑已有规则的视图函数
def edit_rule(request, rule_id):
    # 获取要编辑的规则，不存在则返回404
    rule = get_object_or_404(Rule, id=rule_id)

    if request.method == 'POST':
        # 绑定表单数据并验证
        form = RuleForm(request.POST, instance=rule)
        if form.is_valid():
            # 保存更新（自动更新updated_at字段）
            form.save()
            messages.success(request, "规则已成功更新！")
            # 重定向到该规则所属分类的详情页
            return redirect('rule_detail', rule_type=rule.rule_type)
        else:
            messages.error(request, "表单数据有误，请检查后重新提交")
    else:
        # GET请求：初始化表单并填充当前规则数据
        form = RuleForm(instance=rule)

    # 渲染编辑页面
    return render(request, 'counselors/edit_rule.html', {
        'form': form,
        'rule': rule,
        'page_title': f"编辑规则：{rule.item_name}"
    })


# 删除规则的视图函数
def delete_rule(request, rule_id):
    rule = get_object_or_404(Rule, id=rule_id)
    # 记录规则所属分类，用于删除后重定向
    rule_type = rule.rule_type

    if request.method == 'POST':
        # 执行删除操作
        rule.delete()
        messages.success(request, "规则已成功删除")
        # 重定向到所属分类的详情页
        return redirect('rule_detail', rule_type=rule_type)

    # 如果是GET请求，不允许直接访问删除页面，重定向到详情页
    messages.error(request, "请通过确认弹窗删除规则")
    return redirect('rule_detail', rule_type=rule_type)


# 按规则类型分类查询
def rules_management(request):
    rules = {
        'student_competition_rules': Rule.objects.filter(rule_type='student-competition'),
        'research_achievement_rules': Rule.objects.filter(rule_type='research-achievement'),
        'innovation_rules': Rule.objects.filter(rule_type='innovation-entrepreneurship'),
        'comprehensive_rules': Rule.objects.filter(rule_type='comprehensive-performance'),
    }
    return render(request, 'counselors/rules.html', rules)

