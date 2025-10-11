# 学生应用的模型定义。

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator


# 学生档案
class StudentProfile(models.Model):
    # 与Django自带的用户模型建立一对一关联
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        related_name='profile'  # 反向关联名称
    )
    # 学生属性
    full_name = models.CharField("姓名", max_length=100, blank=True)
    student_id = models.CharField("学号", max_length=20, unique=True,
                                  validators=[RegexValidator(regex=r'^\d{8,20}$', message='学号必须是8-20位数字')])
    grade = models.CharField("年级", max_length=20, blank=True)
    college = models.CharField("学院", max_length=100, blank=True)
    department = models.CharField("系别", max_length=100, blank=True)
    major = models.CharField("专业", max_length=100, blank=True)
    enrollment_year = models.PositiveIntegerField("入学年份", null=True, blank=True, help_text="例如：2023")

    GENDER_CHOICES = [
        ('M', '男'),
        ('F', '女'),
        ('O', '其他'),
    ]
    gender = models.CharField("性别", max_length=1, choices=GENDER_CHOICES, blank=True)
    ethnicity = models.CharField("民族", max_length=50, blank=True)
    political_status = models.CharField("政治面貌", max_length=50, blank=True)
    id_card = models.CharField("身份证号", max_length=18, blank=True,
                               validators=[RegexValidator(regex=r'^\d{17}[\dXx]$', message='请输入有效的身份证号')])

    phone = models.CharField("手机号", max_length=11, blank=True, help_text="请输入11位手机号码")
    email = models.EmailField("邮箱", blank=True, help_text="请输入有效的邮箱地址")

    def __str__(self):
        return self.full_name or self.student_id or str(self.user)


# 学生提交信息
class Submission(models.Model):
    # 预设加分项类型选项
    AWARD_PAPER = 'award_paper'
    COMPETITION = 'competition'
    VOLUNTEER = 'volunteer'
    SCHOLARSHIP = 'scholarship'
    OTHER = 'other'

    CATEGORY_CHOICES = [
        (AWARD_PAPER, '获奖论文'),
        (COMPETITION, '竞赛获奖'),
        (VOLUNTEER, '志愿服务'),
        (SCHOLARSHIP, '奖学金'),
        (OTHER, '其他'),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, verbose_name="学生")
    category = models.CharField("加分项类型", max_length=20, choices=CATEGORY_CHOICES, default=OTHER)
    remarks = models.TextField("备注", blank=True, default="")
    file = models.FileField("提交文件", upload_to='uploads/', null=True, blank=True)
    self_rating = models.DecimalField("自评加分", max_digits=5, decimal_places=1, default=0)
    approved = models.BooleanField("已审核通过", default=False)
    rejected = models.BooleanField(default=False, verbose_name='已驳回')
    reject_reason = models.TextField(blank=True, null=True, verbose_name='驳回理由')
    approved_score = models.DecimalField("审核加分", max_digits=5, decimal_places=1, null=True, blank=True)
    timestamp = models.DateTimeField("提交时间", auto_now_add=True)

    def __str__(self):
        student_name = self.student.full_name or self.student.user.username
        return f"提交#{self.id} - {student_name} - {self.get_category_display()}"