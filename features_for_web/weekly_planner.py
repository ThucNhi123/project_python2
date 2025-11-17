import math
import pandas as pd
from dataclasses import dataclass
from typing import Literal, Tuple, List, Optional

# 1) Tiện ích dựng feature row đúng như mô hình đã train 
def _age_group(age: float) -> str:
    if age <= 30: return "18-30"
    if age <= 45: return "31-45"
    if age <= 60: return "46-60"
    return "61+"

def make_feature_row(
    age: float, sex: str, height_cm: float, weight_kg: float,
    duration_min: float, heart_rate_bpm: float, body_temp_c: float = 37.0
) -> pd.DataFrame:
    BMI = weight_kg / ((height_cm / 100.0) ** 2)
    Duration_per_Heart = duration_min / heart_rate_bpm if heart_rate_bpm > 0 else 0.0
    Intensity = heart_rate_bpm * duration_min
    Temp_per_Minute = body_temp_c / duration_min if duration_min > 0 else 0.0
    Age_Group = _age_group(age)

    row = {
        "Age": age,
        "Height": height_cm,
        "Weight": weight_kg,
        "Duration": duration_min,
        "Heart_Rate": heart_rate_bpm,
        "Body_Temp": body_temp_c,
        "BMI": BMI,
        "Duration_per_Heart": Duration_per_Heart,
        "Intensity": Intensity,
        "Temp_per_Minute": Temp_per_Minute,
        "Age_Group": Age_Group,
        "Sex": sex,             
    }
    return pd.DataFrame([row])

def predict_kcal(model, age, sex, height_cm, weight_kg, duration_min, heart_rate_bpm, body_temp_c=37.0) -> float:
    Xrow = make_feature_row(age, sex, height_cm, weight_kg, duration_min, heart_rate_bpm, body_temp_c)
    kcal = float(model.predict(Xrow)[0])
    return max(0.0, kcal)

# 2) Giải ngược bằng Binary Search theo Duration hoặc theo HR
def solve_duration_for_target(
    model, target_kcal: float, age: float, sex: str, height_cm: float, weight_kg: float,
    base_hr: float, max_minutes: float, body_temp_c: float = 37.0, tol: float = 0.5, max_iter: int = 40
) -> Tuple[float, float, bool]:
    """
    Trả về: (duration_gợi_ý, kcal_dự_kiến, feasible?)
    - Nếu không khả thi với max_minutes tại HR cố định -> feasible=False và duration = max_minutes (kèm kcal đạt được).
    """
    # Nếu ngay cả khi tập max minutes cũng vượt target
    lo, hi = 0.0, max_minutes
    kcal_hi = predict_kcal(model, age, sex, height_cm, weight_kg, hi, base_hr, body_temp_c)
    if kcal_hi + tol < target_kcal:  
        return hi, kcal_hi, False

    # Binary search
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        kcal_mid = predict_kcal(model, age, sex, height_cm, weight_kg, mid, base_hr, body_temp_c)
        if abs(kcal_mid - target_kcal) <= tol: 
            return mid, kcal_mid, True
        if kcal_mid < target_kcal:
            lo = mid
        else:
            hi = mid
    # Sau max_iter, trả về hi (cận đạt mục tiêu)
    kcal_hi = predict_kcal(model, age, sex, height_cm, weight_kg, hi, base_hr, body_temp_c)
    return hi, kcal_hi, True

def solve_hr_for_target(
    model, target_kcal: float, age: float, sex: str, height_cm: float, weight_kg: float,
    duration_min: float, hr_min: float = 90, hr_max: float = 185,
    body_temp_c: float = 37.0, tol: float = 0.5, max_iter: int = 40
) -> Tuple[float, float, bool]:
    """
    Trả về: (HR_gợi_ý, kcal_dự_kiến, feasible?)
    - Nếu không khả thi trong [hr_min, hr_max] -> feasible=False + trả về (hr_max, kcal đạt được ở hr_max)
    """
    lo, hi = hr_min, hr_max
    kcal_hi = predict_kcal(model, age, sex, height_cm, weight_kg, duration_min, hi, body_temp_c)
    if kcal_hi + tol < target_kcal:
        return hi, kcal_hi, False

    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        kcal_mid = predict_kcal(model, age, sex, height_cm, weight_kg, duration_min, mid, body_temp_c)
        if abs(kcal_mid - target_kcal) <= tol:
            return mid, kcal_mid, True
        if kcal_mid < target_kcal:
            lo = mid
        else:
            hi = mid
    kcal_hi = predict_kcal(model, age, sex, height_cm, weight_kg, duration_min, hi, body_temp_c)
    return hi, kcal_hi, True

# 3) Bộ tạo kế hoạch tuần
from dataclasses import dataclass
from typing import Literal, Tuple, List, Optional
import pandas as pd

@dataclass
class UserProfile:
    age: float
    sex: str        
    height_cm: float
    weight_kg: float
    body_temp_c: float = 37.0

#---------------------------------------------
def distribute_targets(
    weekly_target: float,
    days: int,
    mode: Literal["equal","pyramid"]="equal",
    peak_index: Optional[int]=None
) -> List[float]:
    """Chia mục tiêu tuần thành mục tiêu từng buổi."""
    if mode == "equal" or days <= 1:
        return [weekly_target / days] * days
    
    # --- pyramid ---
    mid = (days - 1) / 2.0 if peak_index is None else peak_index
    factors = []
    for i in range(days):
        dist = abs(i - mid)
        factors.append(1.0 + 0.25*(1.0 - dist / max(1, mid)))
    s = sum(factors)
    return [weekly_target * f / s for f in factors]

#---------------------------------------------
def weekly_plan_generator(
    model,
    profile: UserProfile,
    weekly_target_kcal: float,
    days: int,
    max_minutes_per_day: float,
    base_hr: float,
    strategy: Literal["duration_first","hr_first"]="duration_first",
    hr_bounds: Tuple[float,float]=(100, 180),
    split_mode: Literal["equal","pyramid"]="equal",
    start_week_on: Literal["Mon","Sun"]="Mon",
    free_days: Optional[List[str]]=None,
    peak_day: Optional[str]=None
) -> pd.DataFrame:
    """
    Trả về DataFrame 7 ngày gồm: Day, Target_kcal, Suggest_Duration, Suggest_HR, Est_kcal, Feasible, Note.
    Cho phép chỉ định ngày rảnh (free_days) và chọn ngày đỉnh trong pyramid.
    """
    week_days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    if start_week_on == "Sun":
        week_days = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]

    # --- lọc ngày tập ---
    if free_days is None:
        free_days = week_days[:days]
    else:
        free_days = [d for d in week_days if d in free_days]
    if len(free_days) == 0:
        raise ValueError("Không có ngày tập hợp lệ trong free_days")

    # --- xác định index ngày đỉnh ---
    if split_mode == "pyramid":
        if peak_day and peak_day in free_days:
            peak_index = free_days.index(peak_day)
        else:
            peak_index = len(free_days)//2
    else:
        peak_index = None

    # --- chia mục tiêu ---
    per_session_targets = distribute_targets(
        weekly_target_kcal, len(free_days), split_mode, peak_index
    )

    # --- sinh kế hoạch ---
    plan_rows = []
    for dname in week_days:
        if dname in free_days:
            target = per_session_targets[free_days.index(dname)]
            # Giải ngược
            if strategy == "duration_first":
                dur, kcal_est, feasible = solve_duration_for_target(
                    model, target, profile.age, profile.sex,
                    profile.height_cm, profile.weight_kg,
                    base_hr, max_minutes_per_day, profile.body_temp_c
                )
                hr = base_hr
                note = "OK"
                if not feasible:
                    hr2, kcal2, feas2 = solve_hr_for_target(
                        model, target, profile.age, profile.sex,
                        profile.height_cm, profile.weight_kg,
                        dur, hr_min=max(90, hr_bounds[0]), hr_max=hr_bounds[1],
                        body_temp_c=profile.body_temp_c
                    )
                    if feas2:
                        hr, kcal_est, feasible = hr2, kcal2, True
                        note = "OK (tăng HR)"
                    else:
                        hr, kcal_est = hr2, kcal2
                        note = "Không đạt, Duration=max & HR=max"
            else:
                hr, kcal_est, feasible = solve_hr_for_target(
                    model, target, profile.age, profile.sex,
                    profile.height_cm, profile.weight_kg,
                    duration_min=max_minutes_per_day,
                    hr_min=hr_bounds[0], hr_max=hr_bounds[1],
                    body_temp_c=profile.body_temp_c
                )
                dur = max_minutes_per_day
                note = "OK" if feasible else "Không đạt (HR=max)"
            
            plan_rows.append({
                "Day": dname,
                "Target_kcal": round(target,1),
                "Suggest_Duration_min": round(dur,1),
                "Suggest_HR_bpm": round(hr,0),
                "Est_kcal": round(kcal_est,1),
                "Feasible": "Yes" if feasible else "No",
                "Note": note
            })
        else:
            plan_rows.append({
                "Day": dname,
                "Target_kcal": 0.0,
                "Suggest_Duration_min": 0.0,
                "Suggest_HR_bpm": 0.0,
                "Est_kcal": 0.0,
                "Feasible": "-",
                "Note": "Rest"
            })

    return pd.DataFrame(plan_rows)

