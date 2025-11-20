from django.shortcuts import render, redirect
import joblib
import json
from django.http import HttpResponse, JsonResponse
import traceback

from .models import UserProfile
from features_for_web.swap_calo import swap_calories
from features_for_web.weekly_planner import weekly_plan_generator, UserProfile as MLProfile
from features_for_web.class_picker import make_weekly_plan
from features_for_web.what_if import what_if_predict
from tracker.models import UserProfile

# --------------------- LANDING PAGE --------------------------
def landing_page(request):
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

    return render(request, "tracker/landing_page.html")

# --------------------- SAVE SURVEY --------------------------
def save_survey(request):
    if request.method == "POST":

        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        age = int(request.POST.get("age"))
        sex = request.POST.get("sex")
        height = float(request.POST.get("height"))
        weight = float(request.POST.get("weight"))
        heart_rate = float(request.POST.get("heart_rate"))
        body_temp = float(request.POST.get("body_temp"))
        efficiency = float(request.POST.get("efficiency"))
        intensity = int(request.POST.get("intensity"))

        profile, created = UserProfile.objects.update_or_create(
            session_key=session_key,
            defaults={
                "age": age,
                "sex": sex,
                "height": height,
                "weight": weight,
                "heart_rate": heart_rate,
                "body_temp": body_temp,
                "efficiency": efficiency,
                "intensity": intensity,
            }
        )

        return JsonResponse({"status": "success"})

    return JsonResponse({"error": "POST only"}, status=405)

# --------------------- MAIN PAGE --------------------------
def main_views(request):
    session_key = request.session.session_key
    profile = None
    if session_key:
        try:
            profile = UserProfile.objects.get(session_key=session_key)
        except UserProfile.DoesNotExist:
            pass

    return render(request, 'tracker/main_views.html', {"profile": profile})

# --------------------- CALORIE SWAP --------------------------
def calorie_swap(request):
    session_key = request.session.session_key
    profile = None

    if session_key:
        try:
            profile = UserProfile.objects.get(session_key=session_key)
        except UserProfile.DoesNotExist:
            pass

    return render(request, "tracker/calorie_swap.html", {
        "profile": profile
    })

# 🔥 API tính calorie swap
def api_swap_calorie (request):
    """API nhận food_kcal + user_info -> trả về required_minutes, burn_estimate, feasible"""
    if request.method == "POST":
        try: 
            food_name = request.POST.get("food_name")
            quantity = int(request.POST.get("quantity"))
            age = float(request.POST.get("age"))
            sex_raw = request.POST.get("sex", "").lower()
            height = float(request.POST.get("height"))
            weight = float(request.POST.get("weight"))
            heart_rate = float(request.POST.get("heart_rate"))
            max_min = float(request.POST.get("max_min"))
            body_temp = float(request.POST.get("body_temp", 37))
        except: 
            return JsonResponse({"error": "Invalid input"}, status=400)

        if sex_raw in ["female", "nữ", "nu", "f"]:
            sex = "female"
        else:
            sex = "male"

        result = swap_calories(food_name, quantity, age, sex, height, weight, heart_rate, max_min, body_temp)
        return JsonResponse(result)
    
    return JsonResponse({"error": "POST only"}, status=405)

# --------------------- WEEKLY PLAN GENERATOR --------------------------
model = joblib.load("artifacts/best_calorie_model.pkl")

def api_generate_plan(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=400)

    try:
        data = json.loads(request.body)

        weekly_target = float(data["weeklyTarget"])
        max_hours = float(data["maxHours"])
        free_days = data["freeDays"]
        split_mode = data["splitMode"]
        peak_day = data.get("peakDay")

        # --- MAP NGÀY VIỆT → ENGLISH ---
        MAP_DAY = {
            "Thứ 2": "Mon",
            "Thứ 3": "Tue",
            "Thứ 4": "Wed",
            "Thứ 5": "Thu",
            "Thứ 6": "Fri",
            "Thứ 7": "Sat",
            "Chủ nhật": "Sun", 

            # English full
            "Monday": "Mon",
            "Tuesday": "Tue",
            "Wednesday": "Wed",
            "Thursday": "Thu",
            "Friday": "Fri",
            "Saturday": "Sat",
            "Sunday": "Sun",

            # English short
            "Mon": "Mon",
            "Tue": "Tue",
            "Wed": "Wed",
            "Thu": "Thu",
            "Fri": "Fri",
            "Sat": "Sat",
            "Sun": "Sun",
        }

        free_days = [MAP_DAY[d] for d in free_days]
        if peak_day:
            peak_day = MAP_DAY.get(peak_day)

        session_key = request.session.session_key
        db_prof = None
        try:
            db_prof = UserProfile.objects.get(session_key=session_key)
        except:
            pass

        if db_prof:
            SEX_MAP = {
                "Nam": "male",
                "Nữ": "female",
                "Khác": "female"
            }

            profile = MLProfile(
                age = db_prof.age, 
                sex=SEX_MAP.get(db_prof.sex, "female"), 
                height_cm=db_prof.height, 
                weight_kg=db_prof.weight,
                body_temp_c=db_prof.body_temp, 
                heart_rate_bpm=db_prof.heart_rate,
            )
            base_hr = db_prof.heart_rate
        
        else: 
            profile = MLProfile(
                age=21,
                sex="female",
                height_cm=160,
                weight_kg=50,
                body_temp_c=37.0
            )
        

        df = weekly_plan_generator(
            model=model,
            profile=profile,
            weekly_target_kcal=weekly_target,
            days=len(free_days),
            max_minutes_per_day=max_hours * 60,
            base_hr=150,
            split_mode=split_mode,
            free_days=free_days,
            peak_day=peak_day,
        )

        return JsonResponse({
            "status": "success",
            "plan": df.to_dict(orient="records")
        })

    except Exception as e:
        print("ERROR:", e)
        return JsonResponse({"error": "Invalid input", "detail": str(e)}, status=400)

def weekly_plan_generator_view(request):
    return render(request, 'tracker/weekly_plan_generator.html')

# --------------------- GOAL TRANSLATOR --------------------------

def goal_translator(request):
    return render(request, 'tracker/goal_translator.html')

def api_goal_translator(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=400)

    try:
        data = json.loads(request.body)

        weight_change = float(data["weightChange"])
        max_hours = float(data["maxHours"])
        free_days = data["freeDays"]
        split_mode = data["splitMode"]
        peak_day = data.get("peakDay")

        MAP_DAY = {
            "Thứ 2": "Mon",
            "Thứ 3": "Tue",
            "Thứ 4": "Wed",
            "Thứ 5": "Thu",
            "Thứ 6": "Fri",
            "Thứ 7": "Sat",
            "Chủ nhật": "Sun", 

            # English full
            "Monday": "Mon",
            "Tuesday": "Tue",
            "Wednesday": "Wed",
            "Thursday": "Thu",
            "Friday": "Fri",
            "Saturday": "Sat",
            "Sunday": "Sun",

            # English short
            "Mon": "Mon",
            "Tue": "Tue",
            "Wed": "Wed",
            "Thu": "Thu",
            "Fri": "Fri",
            "Sat": "Sat",
            "Sun": "Sun",
        }

        free_days = [MAP_DAY[d] for d in free_days]
        if peak_day:
            peak_day = MAP_DAY.get(peak_day)

        # --- lấy profile thật nếu có ---
        session_key = request.session.session_key

        db_prof = None
        try:
            db_prof = UserProfile.objects.get(session_key=session_key)
        except:
            pass

        if db_prof: 
            SEX_MAP = {
                "Nam": "male", 
                "Nữ": "female", 
                "Khác": "female"
            }
            profile = MLProfile(
                age=db_prof.age,
                sex=SEX_MAP.get(db_prof.sex, "female"),
                height_cm=db_prof.height,
                weight_kg=db_prof.weight,
                body_temp_c=db_prof.body_temp,
                heart_rate_bpm=db_prof.heart_rate,
            )
            base_hr = db_prof.heart_rate
        else:
            profile = MLProfile(age=21, sex="female", height_cm=160, weight_kg=50)
            base_hr = 150
        
        weekly_kcal = abs(weight_change) * 7700

        plan_df = weekly_plan_generator(
            model=model,
            profile=profile,
            weekly_target_kcal=weekly_kcal,
            days=len(free_days),
            max_minutes_per_day=max_hours * 60,
            base_hr=base_hr,
            split_mode=split_mode,
            free_days=free_days,
            peak_day=peak_day
        )

        return JsonResponse({
            "status": "success",
            "weekly_kcal": weekly_kcal,
            "plan": plan_df.to_dict(orient="records")
        })

    except Exception as e:
        print("ERROR:", e)
        return JsonResponse({"error": "Invalid input", "detail": str(e)}, status=400)

# --------------------- CLASS PICKER --------------------------
def class_picker(request):
    return render(request, 'tracker/class_picker.html')

def class_picker_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)
    
    try:
        data = json.loads(request.body.decode("utf-8"))
    except:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    days_raw = data.get("days", [])
    raw_group = data.get("activity")
    weekly_target = (data.get("weekly_target"))
    weight_kg = data.get("weight")

    DAY_MAP = {
        "Monday": "thứ 2",
        "Tuesday": "thứ 3",
        "Wednesday": "thứ 4",
        "Thursday": "thứ 5",
        "Friday": "thứ 6",
        "Saturday": "thứ 7",
        "Sunday": "chủ nhật",

        "Mon": "thứ 2",
        "Tue": "thứ 3",
        "Wed": "thứ 4",
        "Thu": "thứ 5",
        "Fri": "thứ 6",
        "Sat": "thứ 7",
        "Sun": "chủ nhật",
    }

    days = [DAY_MAP.get(d) for d in days_raw if d in DAY_MAP]
    if not days:
        return JsonResponse({"error": "You haven't selected any workout days!"}, status=400)

    GROUP_MAP = {
        "Outdoor": "ngoài trời",
        "Indoor": "trong nhà",
        "Sports": "thể thao",
        "Resistance": "kháng lực",
        "Art": "nghệ thuật",
    }
    mapped_group = GROUP_MAP.get(raw_group)

    if mapped_group is None:
        return JsonResponse({
            "error": f"Activity group '{raw_group}' is invalid. Valid groups: {list(GROUP_MAP.keys())}"
        }, status=400)

    groups = [mapped_group]  

    if weekly_target is None:
        return JsonResponse({"error": "Missing weekly target"}, status=400)
    
    try:
        weekly_target = float(data.get("weekly_target"))
    except:
        return JsonResponse({"error": "weekly_target must be a number"}, status=400)

    try:
        df = make_weekly_plan(
            days=days,
            groups=groups,
            weight_kg=weight_kg,
            weekly_target_kcal=weekly_target
        )
        html_table = df.to_html(index=False)
        return JsonResponse({"table": html_table})

    except Exception as e:
        print("❌ CLASS PICKER ERROR:", e)
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

# --------------------- WHAT-IF COACH --------------------------
def what_if_coach(request):
    return render(request, 'tracker/what_if_coach.html')

def api_what_if (request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)
    
    #Lấy profile người dùng từ DB
    profile = UserProfile.objects.last()
    if profile is None:
        return JsonResponse({"error": "Chưa có dữ liệu người dùng"}, status = 400)
    
    #Lấy dữ liệu từ form 
    try:
        duration = int(request.POST.get("duration"))
        heartrate = int(request.POST.get("heartrate"))
    except:
        return JsonResponse({"error": "Dữ liệu không hợp lệ"}, status=400)
    
    #Lấy thông tin cơ thẻ từ profile 
    age = profile.age
    height = profile.height
    weight = profile.weight
    body_temp = profile.body_temp

    # Chuẩn hóa giới tính theo mô hình
    sex_raw = profile.sex.lower()
    if sex_raw in ["female", "nữ", "nu", "f"]:
        sex = "female"
    else:
        sex = "male"

    #Chạy Model What if 
    result = what_if_predict (
        age = age, 
        sex = sex, 
        height = height, 
        weight = weight, 
        duration= duration, 
        heart_rate = heartrate, 
        body_temp=body_temp, 
    )

    return JsonResponse ({
        "predicted": result["predicted_kcal"], 
        "compare_duration": result["compare_duration"], 
        "compare_heartrate": result["compare_heartrate"], 
    })