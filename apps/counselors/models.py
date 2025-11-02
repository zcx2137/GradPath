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
    college = models.CharField("所属学院", max_length=100)

    def __str__(self):
        return self.full_name


class Rule(models.Model):
    RULE_TYPE_CHOICES = [
        ('student-competition', '学业竞赛'),
        ('research-achievement', '科研成果'),
        ('innovation-entrepreneurship', '创新创业训练'),
        ('comprehensive-performance', '综合表现加分'),
    ]

    item_name = models.CharField(max_length=200, verbose_name="加分项目名称", null=True, blank=True)
    description = models.TextField(verbose_name="加分标准说明")
    score = models.DecimalField(max_digits=5, decimal_places=1, verbose_name="加分分值", null=True, blank=True)
    remark = models.TextField(blank=True, null=True, verbose_name="备注信息")
    rule_type = models.CharField(max_length=50, choices=RULE_TYPE_CHOICES, verbose_name="规则分类")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "加分规则"
        verbose_name_plural = "加分规则"

    def __str__(self):
        return f"{self.get_rule_type_display()}: {self.item_name}"
