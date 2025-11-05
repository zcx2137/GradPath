from django import forms
from students.models import Rule

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