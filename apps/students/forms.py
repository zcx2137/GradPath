# apps/students/forms.py
from django import forms
from captcha.fields import CaptchaField

class StudentLoginForm(forms.Form):
    student_id = forms.CharField(label='学号', max_length=20)
    password = forms.CharField(label='密码', widget=forms.PasswordInput)
    captcha = CaptchaField(label='验证码')  # 添加验证码字段