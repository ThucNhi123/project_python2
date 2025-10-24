import math
import pandas as pd
from dataclasses import dataclass
from typing import Literal, Tuple, List, Optional

# ----------------- Tiện ích tạo feature -----------------
def _age_group(age: float) -> str:
    if age <= 30: return "18-30"
    if age <= 45: return "31-45"
    if age <= 60: return "46-60"
    return "61+"

def make_feature_row(age: float, sex: str, height_cm: float, weight_kg: float,
                     duration_min: float, heart_rate_bpm: float, body_temp_c: float = 37.0) -> pd.DataFrame:
    BMI = weight_kg / ((height_cm / 100.0) ** 2)
    Duration_per_Heart = duration_min / heart_rate_bpm if heart_rate_bpm > 0 else 0.0
    Intensity = heart_rate_bpm * duration_min
    Temp_per_Minute = body_temp_c / duration_min if duration_min > 0 else 0.0
    Age_Group = _age_group(age)
    row = {
        "Age": age, "Height": height_cm, "Weight": weight_kg,
        "Duration": duration_min, "Heart_Rate": heart_rate_bpm, "Body_Temp": body_temp_c,
        "BMI": BMI, "Duration_per_Heart": Duration_per_Heart,
        "Intensity": Intensity, "Temp_per_Minute": Temp_per_Minute,
        "Age_Group": Age_Group, "Sex": sex
    }
    return pd.DataFrame([row])

def predict_kcal(model, age, sex, height_cm, weight_kg, duration_min, heart_rate_bpm, body_temp_c=37.0) -> float:
    Xrow = make_feature_row(age, sex, height_cm, weight_kg, duration_min, heart_rate_bpm, body_temp_c)
    kcal = float(model.predict(Xrow)[0])
    return max(0.0, kcal)

# ----------------- Tạo cấu trúc dữ liệu -----------------
@dataclass
class UserProfile:
    age: float
    sex: str        
    height_cm: float
    weight_kg: float
    body_temp_c: float = 37.0

# ----------------- Sinh kế hoạch tuần -----------------
def distribute_targets(weekly_target: float, days: int, mode: Literal["equal","pyramid"]="equal", peak_index: Optional[int]=None) -> List[float]:
    if mode == "equal" or days <= 1:
        return [weekly_target / days] * days
    mid = (days - 1) / 2.0 if peak_index is None else peak_index
    factors = []
    for i in range(days):
        dist = abs(i - mid)
        factors.append(1.0 + 0.25*(1.0 - dist / max(1, mid)))
    s = sum(factors)
    return [weekly_target * f / s for f in factors]

# ----------------- Bộ sinh kế hoạch -----------------
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
    """Trả về DataFrame kế hoạch tập luyện cho tuần."""
    week_days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    if start_week_on == "Sun":
        week_days = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]

    if free_days is None:
        free_days = week_days[:days]
    else:
        free_days = [d for d in week_days if d in free_days]
    if len(free_days) == 0:
        raise ValueError("Không có ngày tập hợp lệ trong free_days")

    if split_mode == "pyramid":
        if peak_day and peak_day in free_days:
            peak_index = free_days.index(peak_day)
        else:
            peak_index = len(free_days)//2
    else:
        peak_index = None

    per_session_targets = distribute_targets(weekly_target_kcal, len(free_days), split_mode, peak_index)

    plan_rows = []
    for dname in week_days:
        if dname in free_days:
            target = per_session_targets[free_days.index(dname)]
            plan_rows.append({
                "Day": dname,
                "Target_kcal": round(target,1),
                "Suggest_Duration_min": 45.0,
                "Suggest_HR_bpm": 120,
                "Est_kcal": round(target,1),
                "Feasible": "Yes",
                "Note": "OK"
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

# ----------------- Hàm goal_translator chính -----------------
def goal_translator(
    model,
    profile: UserProfile,
    weight_change_kg_per_week: float,  
    days: int,
    max_minutes_per_day: float,
    base_hr: float,
    strategy: Literal["duration_first","hr_first"]="duration_first",
    hr_bounds: Tuple[float,float]=(100,180),
    split_mode: Literal["equal","pyramid"]="equal",
    start_week_on: Literal["Mon","Sun"]="Mon",
    free_days: Optional[List[str]]=None,
    peak_day: Optional[str]=None
) -> Tuple[pd.DataFrame, float]:
    """Chuyển đổi mục tiêu cân nặng -> kcal/tuần -> kế hoạch buổi tập."""
    weekly_target_kcal = abs(weight_change_kg_per_week) * 7700
    plan_df = weekly_plan_generator(
        model=model,
        profile=profile,
        weekly_target_kcal=weekly_target_kcal,
        days=days,
        max_minutes_per_day=max_minutes_per_day,
        base_hr=base_hr,
        strategy=strategy,
        hr_bounds=hr_bounds,
        split_mode=split_mode,
        start_week_on=start_week_on,
        free_days=free_days,
        peak_day=peak_day
    )
    return plan_df, weekly_target_kcal
