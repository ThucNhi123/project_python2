from django.shortcuts import render, redirect
from django.conf import settings
from .form import PlannerForm
from .planner_logic import make_weekly_plan, swap_days, change_activity
import os
import pandas as pd
import json

# Đường dẫn tuyệt đối đến file dữ liệu CSV
DATA_PATH = os.path.join(settings.BASE_DIR, "exercise_dataset (1).csv")

def planner_view(request):
    """Xử lý trang chủ: Hiển thị form và nhận dữ liệu POST."""
    if request.method == 'POST':
        form = PlannerForm(request.POST)
        if form.is_valid():
            # Lưu dữ liệu form vào session để dùng khi quay lại trang kết quả
            request.session['form_data'] = form.cleaned_data
            
            # Chuyển hướng sang view xử lý kết quả
            return redirect('planner:plan_result')
    else:
        # Nếu có dữ liệu cũ, dùng nó để khởi tạo form
        initial_data = request.session.get('form_data', {})
        form = PlannerForm(initial=initial_data)

    return render(request, 'planner/index.html', {'form': form})

def plan_result_view(request):
    """Tạo kế hoạch và hiển thị kết quả (sau khi form được gửi thành công)."""
    form_data = request.session.get('form_data')
    if not form_data:
        # Nếu không có dữ liệu form, quay về trang chủ
        return redirect('planner:planner_home')

    try:
        # Lấy dữ liệu từ session
        days = form_data['free_days']
        groups = form_data['activity_groups']
        weight_kg = form_data['weight_kg']
        weekly_target_kcal = form_data['weekly_target_kcal']

        # 1. TẠO KẾ HOẠCH BẰNG LOGIC PYTHON
        plan_df = make_weekly_plan(
            days=days,
            groups=groups,
            weight_kg=weight_kg,
            weekly_target_kcal=weekly_target_kcal,
            data_path=DATA_PATH
        )
        
        # 2. LƯU VÀO SESSION (để xử lý chỉnh sửa)
        # Chuyển DataFrame thành JSON string và lưu vào session
        request.session['current_plan_json'] = plan_df.to_json(orient='split')
        
        # 3. CHUẨN BỊ CONTEXT ĐỂ HIỂN THỊ
        plan_html = plan_df.to_html(
            index=False, 
            classes='table table-striped text-center', 
            float_format='%.1f'
        )
        total_kcal = plan_df["Kcal ước tính"].sum()

        context = {
            'plan_html': plan_html,
            'total_kcal': round(total_kcal, 1),
            'target_kcal': weekly_target_kcal,
            'deviation': round(total_kcal - weekly_target_kcal, 1),
            'day_options': plan_df["Ngày"].tolist(),
        }
        return render(request, 'planner/plan_result.html', context)
    
    except Exception as e:
        # Xử lý lỗi
        error_message = f"Lỗi xảy ra khi tạo kế hoạch: {e}"
        return render(request, 'planner/index.html', {'form': PlannerForm(initial=form_data), 'error': error_message})


def modify_plan_view(request):
    """Xử lý các yêu cầu thay đổi kế hoạch (swap hoặc change activity)."""
    if request.method == 'POST':
        action = request.POST.get('action')
        plan_json = request.session.get('current_plan_json')
        form_data = request.session.get('form_data')

        if not plan_json or not form_data:
            return redirect('planner:planner_home')

        # Tải lại DataFrame từ session
        plan_df = pd.read_json(plan_json, orient='split')
        weight_kg = form_data['weight_kg']
        
        message = ""

        if action == 'swap':
            day1 = request.POST.get('day1')
            day2 = request.POST.get('day2')
            plan_df = swap_days(plan_df, day1, day2)
            message = f"✅ Đã hoán đổi kế hoạch giữa **{day1}** và **{day2}**."
        
        elif action == 'change_activity':
            day = request.POST.get('day_to_change')
            # Hàm change_activity có in thông báo, ta sẽ lấy thông báo đó nếu cần
            # Ở đây, ta chỉ cần gọi hàm và nó sẽ tự cập nhật df
            plan_df = change_activity(plan_df, day, DATA_PATH, weight_kg)
            message = f"✅ Đã tự động đổi hoạt động của **{day}** (giữ nguyên mức năng lượng mục tiêu)."
            
        # Lưu kế hoạch mới vào session
        request.session['current_plan_json'] = plan_df.to_json(orient='split')
        
        # Quay lại trang kết quả
        plan_html = plan_df.to_html(index=False, classes='table table-striped text-center', float_format='%.1f')
        total_kcal = plan_df["Kcal ước tính"].sum()

        context = {
            'plan_html': plan_html,
            'total_kcal': round(total_kcal, 1),
            'target_kcal': form_data['weekly_target_kcal'],
            'deviation': round(total_kcal - form_data['weekly_target_kcal'], 1),
            'day_options': plan_df["Ngày"].tolist(),
            'message': message,
        }
        return render(request, 'planner/plan_result.html', context)
    
    return redirect('planner:planner_home')