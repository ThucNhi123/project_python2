from django.shortcuts import render

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
