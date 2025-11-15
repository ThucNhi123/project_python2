from django import forms
# Import các hằng số từ module logic
from .planner_logic import VN_DAY_ORDER, GROUPS

# Tạo danh sách choices
DAY_CHOICES = [(day, day.title()) for day in VN_DAY_ORDER]
GROUP_CHOICES = [(group, group.title()) for group in GROUPS]

class PlannerForm(forms.Form):
    # Dữ liệu số
    weight_kg = forms.FloatField(
        label="Số cân đối mới tuần (kg)",
        min_value=30.0,
        max_value=150.0,
        initial=65.0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'max-width: 250px;'})
    )
    weekly_target_kcal = forms.FloatField(
        label="Số calo tối đa mỗi tuần (kcal)",
        min_value=100.0,
        initial=500.0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'max-width: 250px;'})
    )

    # Ngày nghỉ (Chọn nhiều)
    free_days = forms.MultipleChoiceField(
        label="Chọn ngày rảnh:",
        choices=DAY_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'day-checkboxes'})
    )
    
    # Nhóm hoạt động (Chọn nhiều)
    activity_groups = forms.MultipleChoiceField(
        label="Chọn nhóm hoạt động yêu thích:",
        choices=GROUP_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'group-checkboxes'})
    )