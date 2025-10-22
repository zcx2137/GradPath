# 学生应用的模型定义。

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from decimal import Decimal


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

    academic_comprehensive_score = models.DecimalField(
        "学业综合成绩",  # 辅导员可设置
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True
    )
    academic_expertise_score = models.DecimalField(
        "学术专长成绩",  # 来自学术类材料加分
        max_digits=5,
        decimal_places=1,
        default=0
    )
    comprehensive_performance_score = models.DecimalField(
        "综合表现成绩",  # 来自综合类材料加分
        max_digits=5,
        decimal_places=1,
        default=0
    )
    total_score = models.DecimalField(
        "总成绩",
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True
    )

    # 成绩权重设置（可根据实际需求调整默认值）
    academic_comprehensive_ratio = models.DecimalField(
        "学业综合成绩权重",
        max_digits=3,
        decimal_places=2,
        default=0.6  # 60%
    )
    academic_expertise_ratio = models.DecimalField(
        "学术专长成绩权重",
        max_digits=3,
        decimal_places=2,
        default=0.2  # 20%
    )
    comprehensive_performance_ratio = models.DecimalField(
        "综合表现成绩权重",
        max_digits=3,
        decimal_places=2,
        default=0.2  # 20%
    )

    def __str__(self):
        return self.full_name or self.student_id or str(self.user)

    def get_rank(self):
        """计算学生的排名（按总分降序）"""
        all_students = StudentProfile.objects.exclude(total_score__isnull=True)
        total_count = all_students.count()

        # 总分高于当前学生的人数 + 1 就是排名
        higher_count = all_students.filter(total_score__gt=self.total_score).count()
        return (higher_count + 1, total_count)

    def save(self, *args, **kwargs):
        # 自动计算总成绩：各项成绩 × 对应权重之和
        if (self.academic_comprehensive_score is not None and
                self.academic_expertise_ratio is not None and
                self.comprehensive_performance_ratio is not None):
            self.total_score = (
                    Decimal(self.academic_comprehensive_score) * self.academic_comprehensive_ratio +
                    Decimal(self.academic_expertise_score) * self.academic_expertise_ratio +
                    Decimal(self.comprehensive_performance_score) * self.comprehensive_performance_ratio
            )
        super().save(*args, **kwargs)


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