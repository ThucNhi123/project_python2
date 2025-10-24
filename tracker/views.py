from django.shortcuts import render
from features_for_web.weekly_planner import UserProfile, goal_translator


def index(request):
    if request.method == "POST":
        weight = float(request.POST.get("weight"))
        activity = request.POST.get("activity")
        time = int(request.POST.get("time"))

        MET_values = {
            "walking": 3.5,
            "running": 8.0,
            "cycling": 7.5,
            "swimming": 6.0,
        }

        met = MET_values.get(activity, 1)
        total_calories = met * 3.5 * weight / 200 * time

        # Tạo dữ liệu biểu đồ: calories theo từng phút
        calories_list = []
        for t in range(1, time + 1):
            cal = met * 3.5 * weight / 200 * t
            calories_list.append(round(cal, 2))

        return render(request, "tracker/result.html", {
            "calories": round(total_calories, 2),
            "labels": list(range(1, time + 1)),
            "data": calories_list,
        })

    return render(request, "tracker/index.html")

def today_calories(request):
    calories_burned = None  # biến để lưu kết quả
    activity = None
    duration = None

    if request.method == 'POST':
        weight = float(request.POST.get('weight', 0))
        duration = float(request.POST.get('duration', 0))
        activity = request.POST.get('activity')

        # Bảng MET
        met_values = {
            'walking': 3.8,
            'running': 7.5,
            'cycling': 6.8,
            'swimming': 8.0,
            'yoga': 3.0
        }

        met = met_values.get(activity, 3.5)
        calories_burned = round(met * 3.5 * weight / 200 * duration, 2)

    return render(request, 'tracker/burn_calories.html', {
        'calories': calories_burned,
        'activity': activity,
        'duration': duration,
    })
    

WEEKLY_PLAN_CACHE = None

def goal_plan(request):
    global WEEKLY_PLAN_CACHE
    plan_df = None
    weekly_target = None

    if request.method == 'POST':
        # --- nhập dữ liệu từ form ---
        weight_change = float(request.POST.get('weight_change', 0))
        days = int(request.POST.get('days', 5))
        max_minutes = float(request.POST.get('max_minutes', 60))
        base_hr = float(request.POST.get('base_hr', 120))
        strategy = request.POST.get('strategy', 'duration_first')

        # --- giả lập profile ---
        profile = UserProfile(age=25, sex="female", height_cm=165, weight_kg=60)

        # --- giả lập mô hình (demo: random thay vì model.predict thật) ---
        class FakeModel:
            def predict(self, X):
                # kcal = hệ số đơn giản
                return [0.09 * X["Heart_Rate"].iloc[0] * X["Duration"].iloc[0]]
        model = FakeModel()

        plan_df, weekly_target = goal_translator(
            model=model,
            profile=profile,
            weight_change_kg_per_week=weight_change,
            days=days,
            max_minutes_per_day=max_minutes,
            base_hr=base_hr,
            strategy=strategy
        )

        WEEKLY_PLAN_CACHE = plan_df  # Lưu tạm để trang daily dùng lại
        plan_html = plan_df.to_html(classes="table table-hover text-center table-bordered align-middle", index=False)

        return render(request, 'tracker/goal_plan.html', {
            'plan_html': plan_html,
            'weekly_target': weekly_target,
            'weight_change': weight_change,
            'plan_df': plan_df.to_dict(orient="records")
        })

    return render(request, 'tracker/goal_plan.html')


def daily_detail(request, day_name):
    """Hiển thị chi tiết ngày tập"""
    global WEEKLY_PLAN_CACHE
    if WEEKLY_PLAN_CACHE is None:
        return render(request, 'tracker/daily_detail.html', {'error': "Chưa có kế hoạch tuần!"})

    # tìm hàng theo tên ngày
    row = WEEKLY_PLAN_CACHE[WEEKLY_PLAN_CACHE["Day"] == day_name].iloc[0]
    return render(request, 'tracker/daily_detail.html', {'day': row})

