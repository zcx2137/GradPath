from django.db import models
from django.contrib.auth.models import User

class CounselorProfile(models.Model):
    """辅导员档案模型，关联Django用户系统"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='counselor_profile'
    )
    full_name = models.CharField("姓名", max_length=100)
    employee_id = models.CharField("工号", max_length=20, unique=True)
    college = models.CharField("所属学院", max_length=100, blank=True, default="无")
    grade = models.CharField("负责年级", max_length=20, blank=True, default="无")

    def __str__(self):
        return f"{self.full_name}（{self.college} {self.grade}）"