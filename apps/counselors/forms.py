from django import forms
from students.models import Rule
from captcha.fields import CaptchaField


class RuleForm(forms.ModelForm):
    class Meta:
        model = Rule
        fields = ['item_name', 'description', 'score', 'remark', 'rule_type']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': '请输入详细的加分标准...'}),
            'remark': forms.Textarea(attrs={'rows': 2, 'placeholder': '可选：补充说明或注意事项...'}),
            'score': forms.NumberInput(attrs={'min': 0, 'step': 0.5, 'placeholder': '例如：2.5'}),
            'item_name': forms.TextInput(attrs={'placeholder': '例如：国家级数学竞赛一等奖'}),
        }
        labels = {
            'item_name': '加分项目名称',
            'description': '加分标准说明',
            'score': '加分分值',
            'remark': '备注信息',
            'rule_type': '规则分类'
        }

    def clean_score(self):
        """验证分值必须为正数"""
        score = self.cleaned_data.get('score')
        if score is not None and score <= 0:
            raise forms.ValidationError("加分分值必须大于0")
        return score


# 辅导员登录表单（含验证码）
class CounselorLoginForm(forms.Form):
    # 辅导员账号字段（可根据你的业务调整，比如工号/手机号/用户名）
    counselor_id = forms.CharField(label='工号', max_length=20, required=True)
    # 密码字段（密码输入框）
    password = forms.CharField(label='密码', widget=forms.PasswordInput, required=True)
    # 验证码字段（核心：和学生端一样添加CaptchaField）
    captcha = CaptchaField(label='验证码')