"""学生应用的模型定义。
此文件定义了与学生相关的数据库模型，例如学生档案。
"""

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
    student_id = models.CharField("学号", max_length=20, unique=True, validators=[RegexValidator(regex=r'^\d{10,20}$', message='学号必须是10-20位数字')])
    major = models.CharField("专业", max_length=100, blank=True)
    enrollment_year = models.PositiveIntegerField("入学年份", null=True, blank=True, help_text="例如：2023")
    college = models.CharField("学院", max_length=100, blank=True)
    phone = models.CharField("手机号", max_length=11,  blank=True, help_text="请输入11位手机号码")
    email = models.EmailField("邮箱", blank=True, unique=True, help_text="请输入有效的邮箱地址")

    def __str__(self):
        return self.full_name or self.student_id or str(self.user)


# 学生提交信息
class Submission(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, verbose_name="学生")
    description = models.TextField("描述", blank=True, default="")
    file = models.FileField("提交文件", upload_to='uploads/', null=True,blank=True)
    approved = models.BooleanField("已审核通过", default=False)
    timestamp = models.DateTimeField("提交时间", auto_now_add=True)

    def __str__(self):
        """返回模型的字符串表示形式。"""
        student_name = self.student.full_name or self.student.user.username
        return f"提交#{self.id} - {student_name}"