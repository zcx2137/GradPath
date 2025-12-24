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
from django.http import HttpResponse,Http404
import csv
from django.db.models import Q


# 辅导员注册表单
class CounselorRegistrationForm(forms.Form):
    employee_id = forms.CharField(label='工号', max_length=20)
    full_name = forms.CharField(label='姓名', max_length=100)
    college = forms.ChoiceField(
        label='所属学院',
        choices=[
            ('info', '信息学院'),
            ('other', '其他'),
        ]
    )
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

    counselor = request.user.counselor_profile
    # 获取当前辅导员所在学院和负责年级
    counselor_college = counselor.college
    counselor_grade = counselor.grade

    # 获取待审核申请(只显示本学院学生的申请)
    latest_pending_submissions = Submission.objects.filter(
        approved=False,
        rejected=False,
        student__college=counselor_college,  # 过滤学生学院
        student__grade=counselor_grade       # 过滤学生年级
    ).select_related('student').order_by('-timestamp')[:5]

    # 辅导员控制面板中的待审核数量统计
    pending_count = Submission.objects.filter(
        approved=False,
        rejected=False,
        student__college=counselor_college,  # 过滤学生学院
        student__grade=counselor_grade       # 过滤学生年级
    ).count()

    # 计算本周处理数
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    handled_this_week = Submission.objects.filter(
        approved=True,
        timestamp__date__gte=start_of_week,
        student__college=counselor_college,  # 过滤学生学院
        student__grade=counselor_grade       # 过滤学生年级
    ).count()

    # 计算当前生效的加分规则总数
    rules_count = Rule.objects.count()

    # 只统计本学院本年级的学生
    total_students = StudentProfile.objects.filter(
        college=counselor_college,
        grade=counselor_grade
    ).count()

    return render(request, 'counselors/dashboard.html', {
        'pending_count': pending_count,
        'total_students': total_students,
        'latest_pending_submissions': latest_pending_submissions,
        'rules_count': rules_count,  # 传递规则数量到模板
        'handled_this_week': handled_this_week  # 传递周处理数到模板
    })


# 辅导员个人信息编辑表单
class CounselorProfileForm(forms.ModelForm):
    class Meta:
        model = CounselorProfile
        fields = ['full_name']  # 可编辑的字段


# 辅导员个人信息页面
@login_required
def counselor_profile(request):
    # 验证是否为辅导员
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    profile = request.user.counselor_profile

    if request.method == 'POST':
        form = CounselorProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, '个人信息已更新')
            return redirect('counselor_profile')
    else:
        form = CounselorProfileForm(instance=profile)

    return render(request, 'counselors/profile.html', {
        'profile': profile,
        'form': form
    })


# 审核材料
@login_required
def review_submissions(request):
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    counselor_college = request.user.counselor_profile.college
    counselor_grade = request.user.counselor_profile.grade

    pending_submissions = Submission.objects.filter(
        approved=False,  # 未通过
        rejected=False,  # 未驳回
        student__college=counselor_college,     # 仅显示本学院学生的提交
        student__grade=counselor_grade          # 仅显示本年级学生的提交
    ).select_related('student').order_by('-timestamp')  # 保留预加载 student，避免模板报错

    return render(request, 'counselors/review_submissions.html', {
        'submissions': pending_submissions  # 传给模板的只有待审核数据
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
        submission.reviewer = request.user.counselor_profile
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
            content=f"您提交的「{submission.category.get_group_display()} - {submission.category.name}」材料已审核通过，核定加分：{submission.approved_score}分",
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
        submission.reviewer = request.user.counselor_profile
        submission.save()

        # 创建"审核驳回"通知
        Notification.objects.create(
            recipient=submission.student.user,  # 接收通知的学生用户
            title="材料审核未通过",
            content=f"您提交的「{submission.category.get_group_display()} - {submission.category.name}」材料未通过审核，原因：{submission.reject_reason}",
            type='submission'  # 提交审核类型通知
        )

    return redirect('review_submissions')


# 审核详情页
@login_required
def review_detail(request, submission_id):
    # 验证是否为辅导员
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    counselor = request.user.counselor_profile
    # 查询指定ID的提交，同时过滤本学院、本年级（确保权限），不限制状态（包括已审核）
    try:
        submission = Submission.objects.get(
            id=submission_id,
            student__college=counselor.college,  # 仅本学院
            student__grade=counselor.grade  # 仅本年级
        )
    except Submission.DoesNotExist:
        raise Http404("No Submission matches the given query.")  # 明确404原因

    return render(request, 'counselors/review_detail.html', {
        'submission': submission
    })


# 已审核材料页面
@login_required
def reviewed_submissions(request):
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    counselor = request.user.counselor_profile
    counselor_college = counselor.college
    counselor_grade = counselor.grade

    # 修正：位置参数（Q对象）放在关键字参数前面
    reviewed_submissions = Submission.objects.filter(
        # Q对象作为位置参数，放在最前面
        Q(approved=True) | Q(rejected=True),
        # 关键字参数放在后面
        reviewer=counselor,
        student__college=counselor_college,
        student__grade=counselor_grade
    ).select_related('student', 'reviewer').order_by('-timestamp')

    return render(request, 'counselors/reviewed_submissions.html', {
        'submissions': reviewed_submissions
    })


# 审核撤销功能
@login_required
def reset_submission(request, submission_id):
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    submission = get_object_or_404(Submission, id=submission_id, reviewer=request.user.counselor_profile)

    if request.method == 'POST':
        # 如果之前是通过的，需要减去已加的分数
        if submission.approved:
            student = submission.student
            score = Decimal(submission.approved_score or 0)
            academic_categories = ['thesis', 'competition', 'research', 'other_academic']
            comprehensive_categories = ['volunteer', 'leadership', 'social_practice', 'other_comprehensive']

            if submission.category in academic_categories:
                student.academic_expertise_score -= score
            elif submission.category in comprehensive_categories:
                student.comprehensive_performance_score -= score
            student.save()

        # 重置审核状态
        submission.approved = False
        submission.rejected = False
        submission.approved_score = None
        submission.reject_reason = None
        submission.reviewer = None
        submission.save()

        # 创建通知
        Notification.objects.create(
            recipient=submission.student.user,
            title="材料审核状态更新",
            content=f"您提交的「{submission.category.get_group_display()} - {submission.category.name}」材料审核状态已重置，将重新审核",
            type='submission'
        )

        return redirect('reviewed_submissions')

    return render(request, 'counselors/confirm_reset.html', {'submission': submission})


# 查看学生信息
@login_required
def view_all_students(request):
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    counselor_college = request.user.counselor_profile.college
    counselor_grade = request.user.counselor_profile.grade
    students = StudentProfile.objects.filter(
        college=counselor_college,  # 学院过滤
        grade=counselor_grade       # 年级过滤
    ).order_by('-total_score')

    return render(request, 'counselors/all_students.html', {
        'students': students
    })


@login_required
def export_students(request):
    # 验证辅导员身份
    if not hasattr(request.user, 'counselor_profile'):
        return redirect('login')

    # 创建CSV响应
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="学生信息.csv"'

    # 定义需要导出的字段
    fields = [
        '学号', '姓名', '学院', '专业', '入学年份',
        '学业综合成绩', '学术专长成绩', '综合表现成绩', '总成绩'
    ]

    writer = csv.writer(response)
    writer.writerow(fields)  # 写入表头

    # 获取所有学生信息并写入CSV
    students = StudentProfile.objects.all().order_by('-total_score')
    for student in students:
        writer.writerow([
            student.student_id,
            student.full_name,
            student.college,
            student.major,
            student.enrollment_year or '',
            student.academic_comprehensive_score or '',
            student.academic_expertise_score,
            student.comprehensive_performance_score,
            student.total_score or ''
        ])

    return response


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

