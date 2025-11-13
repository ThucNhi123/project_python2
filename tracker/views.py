from django.shortcuts import render, redirect
from features_for_web.weekly_planner import UserProfile, goal_translator
from django.http import HttpResponse, JsonResponse

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

def main_views(request):
    saved = request.session.get("survey", {})
    return render(request, 'tracker/main_views.html', {"saved": saved})

def save_survey(request):
    if request.method == "POST":
        data = request.POST

        request.session["survey"] = {
            "age": data.get("age"),
            "gender": data.get("gender"),
            "height": data.get("height"),
            "weight": data.get("weight"),
            "bpm": data.get("bpm"),
            "temperature": data.get("temperature"),
            "efficiency": data.get("efficiency"),
            "intensity": data.get("intensity"),
        }

        return JsonResponse({"status": "success"})

def weekly_plan_generator(request):
    return render(request, 'tracker/weekly_plan_generator.html')

def goal_translator(request):
    return render(request, 'tracker/goal_translator.html')

def class_picker(request):
    return render(request, 'tracker/class_picker.html')

def what_if_coach(request):
    return render(request, 'tracker/what_if_coach.html')

def calorie_swap(request):
    return render(request, 'tracker/calorie_swap.html')
