# -*- coding: utf-8 -*-
"""
Weekly Activity Planner – chọn hoạt động theo ngày trong tuần để đạt target kcal
Yêu cầu đầu bài:
- Mở đầu code bằng đoạn load model (có thể không tồn tại -> sẽ cảnh báo và fallback):
    import joblib
    MODEL_PATH = "artifacts/best_calorie_model.pkl"
    model = joblib.load(MODEL_PATH)
    print(model)

- Input:
    days: list[str]  (VD: ["thứ 2", "thứ 4", "thứ 6", "chủ nhật"])
    groups: list[str]  (chọn bất kỳ trong: ["ngoài trời","trong nhà","thể thao","kháng lực","nghệ thuật"])
    weight_kg: float
    weekly_target_kcal: float

- Output:
    Bảng gồm: ngày | hoạt động | thời gian (60–120 phút) | kcal  (tổng gần với target)
    + Hỗ trợ đổi cặp hành động giữa 2 ngày.

Ghi chú:
- Dữ liệu hoạt động lấy từ file "exercise_dataset (1).csv" với cột "Activity, Exercise or Sport (1 hour)" và "Calories per kg".
- "Calories per kg" ≈ MET (kcal/kg/giờ). kcal ước tính = MET * weight_kg * (minutes/60).
"""


from __future__ import annotations


# ===== 1) IMPORTS CHUNG =====
import math
import random
from dataclasses import dataclass
from typing import List, Dict, Tuple
import pandas as pd
from pathlib import Path

# ===== 2) HÀM TIỆN ÍCH =====

VN_DAY_ORDER = ["thứ 2","thứ 3","thứ 4","thứ 5","thứ 6","thứ 7","chủ nhật"]
EN_DAY_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

def normalize_day_label(day: str) -> str:
    d = day.strip().lower()
    mapping = {
        "thu 2":"thứ 2","thu2":"thứ 2","monday":"thứ 2",
        "thu 3":"thứ 3","thu3":"thứ 3","tuesday":"thứ 3",
        "thu 4":"thứ 4","thu4":"thứ 4","wednesday":"thứ 4",
        "thu 5":"thứ 5","thu5":"thứ 5","thursday":"thứ 5",
        "thu 6":"thứ 6","thu6":"thứ 6","friday":"thứ 6",
        "thu 7":"thứ 7","thu7":"thứ 7","saturday":"thứ 7",
        "chu nhat":"chủ nhật","chunhat":"chủ nhật","sunday":"chủ nhật",
    }
    return mapping.get(d, d)

def load_activity_db(path: str | Path = "exercise_dataset (1).csv") -> pd.DataFrame:
    """Đọc file data và chuẩn hoá cột."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Không thấy file dữ liệu: {p.resolve()}")
    raw = pd.read_csv(p)
    # Chuẩn hoá tên cột
    df = raw.rename(columns={
        "Activity, Exercise or Sport (1 hour)": "activity",
        "Calories per kg": "cpk_per_hour",
    }).copy()
    # Loại bỏ dòng NA
    df = df.dropna(subset=["activity","cpk_per_hour"])
    # Bỏ trùng
    df = df.drop_duplicates(subset=["activity"]).reset_index(drop=True)
    # Tạo cột lower để match từ khoá nhóm
    df["activity_lower"] = df["activity"].str.lower().str.strip()
    return df[["activity","activity_lower","cpk_per_hour"]]

# ===== 3) PHÂN NHÓM HOẠT ĐỘNG BẰNG KEYWORDS =====

GROUPS = ["ngoài trời","trong nhà","thể thao","kháng lực","nghệ thuật"]

GROUP_KEYWORDS: Dict[str, List[str]] = {
    "ngoài trời": [
        "run","walk","hike","cycling","bike","row","stair","climb",
        "jump rope","paddle","canoe","kayak","skate","ski","surf","swim",
        "mountain","bmx","hiking","jog"
    ],
    "trong nhà": [
        "treadmill","elliptical","aerobic","yoga","stair","indoor",
        "pilates","stationary","rowing machine","step aerobics","spin"
    ],
    "thể thao": [
        "basketball","football","soccer","tennis","badminton","squash","table tennis",
        "volleyball","baseball","handball","racquetball","hockey","rugby","golf"
    ],
    "kháng lực": [
        "weight","lifting","strength","resistance","calisthenics","circuit",
        "body building","pushup","situp","crossfit","kettlebell"
    ],
    "nghệ thuật": [
        "dance","dancing","ballet","ballroom","modern","zumba","aerobic dance"
    ],
}

def tag_group(activity_lower: str) -> List[str]:
    tags = []
    for g, kws in GROUP_KEYWORDS.items():
        for kw in kws:
            if kw in activity_lower:
                tags.append(g)
                break
    if not tags:
        # fallback nhẹ: phân loại bề mặt
        if any(k in activity_lower for k in ["dance","yoga","ballet","ballroom","zumba"]):
            tags.append("nghệ thuật")
        elif any(k in activity_lower for k in ["weight","lift","resist","circuit","kettlebell","pushup","situp","calisthenics"]):
            tags.append("kháng lực")
        elif any(k in activity_lower for k in ["basket","tennis","soccer","football","badminton","squash","volley","golf","hockey","rugby"]):
            tags.append("thể thao")
        elif any(k in activity_lower for k in ["treadmill","elliptical","indoor","rowing machine","step"]):
            tags.append("trong nhà")
        else:
            tags.append("ngoài trời")
    return list(dict.fromkeys(tags))  # unique, giữ thứ tự

def build_pool_by_groups(df: pd.DataFrame, chosen_groups: List[str], min_per_group: int = 3) -> pd.DataFrame:
    cg = [g for g in chosen_groups if g in GROUPS]
    if not cg:
        raise ValueError(f"Nhóm hợp lệ: {GROUPS}")
    df = df.copy()
    df["groups"] = df["activity_lower"].apply(tag_group)
    # Lọc theo nhóm đã chọn (ít nhất khớp 1 nhãn)
    mask = df["groups"].apply(lambda gs: any(g in gs for g in cg))
    pool = df[mask].copy()
    # Đảm bảo mỗi nhóm có tối thiểu min_per_group hoạt động (nếu thiếu -> in cảnh báo)
    for g in cg:
        n = sum(pool["groups"].apply(lambda gs: g in gs))
        if n < min_per_group:
            print(f"[Cảnh báo] Nhóm '{g}' chỉ có {n} hoạt động khớp từ khoá trong data.")
    return pool.reset_index(drop=True)

# ===== ) LOGIC CHỌN HOẠT ĐỘNG THEO NGÀY =====

from dataclasses import dataclass

@dataclass
class DayPlan:
    day: str
    activity: str
    minutes: int
    kcal: float
    cpk_per_hour: float

def estimate_kcal_db(weight_kg: float, minutes: int, cpk_per_hour: float) -> float:
    return float(cpk_per_hour * weight_kg * (minutes/60.0))

def choose_activities_for_days(days: List[str], pool: pd.DataFrame, weekly_target_kcal: float, weight_kg: float) -> List[Tuple[str,str,float]]:
    """
    Trả về danh sách (day, activity, cpk_per_hour).
    Heuristic: aim per-day kcal ~ target/n_days với thời lượng ban đầu 90 phút,
    chọn activity có cpk gần nhất sao cho 3 ngày liên tiếp khác nhau.
    """
    n = len(days)
    target_day = weekly_target_kcal / max(1,n)
    base_minutes = 90
    # Tạo ứng viên sắp xếp theo |cpk*wt*(base_minutes/60) - target_day| tăng dần
    pool = pool.copy()
    pool["score"] = (pool["cpk_per_hour"]*weight_kg*(base_minutes/60.0) - target_day).abs()
    pool_sorted = pool.sort_values("score").reset_index(drop=True)

    picks: List[Tuple[str,str,float]] = []
    used_recent: List[str] = []
    for i, day in enumerate(days):
        # chọn activity đầu tiên không trùng với 2 ngày trước đó
        chosen = None
        for _, row in pool_sorted.iterrows():
            act = row["activity"]
            if len(used_recent) >= 2 and act in used_recent[-2:]:
                continue  # tránh lặp lại trong cửa sổ 3 ngày
            chosen = (day, act, float(row["cpk_per_hour"]))
            break
        if chosen is None:
            # nếu không tìm được do pool quá nhỏ, cho phép trùng với ngày gần nhất nhưng không trùng 2 lần liền
            for _, row in pool_sorted.iterrows():
                act = row["activity"]
                if not used_recent or act != used_recent[-1]:
                    chosen = (day, act, float(row["cpk_per_hour"]))
                    break
        if chosen is None:
            # trường hợp cực đoan – lấy dòng đầu tiên
            r0 = pool_sorted.iloc[0]
            chosen = (day, r0["activity"], float(r0["cpk_per_hour"]))
        picks.append(chosen)
        used_recent.append(chosen[1])
    return picks

def allocate_durations(minutes_low: int, minutes_high: int, picks: List[Tuple[str,str,float]], weight_kg: float, weekly_target_kcal: float) -> List[DayPlan]:
    """
    Phân bổ thời lượng trong [minutes_low, minutes_high] để tổng kcal gần target nhất.
    Greedy: bắt đầu 60' cho tất cả, sau đó bơm thêm vào ngày có suất đốt cao hơn.
    """
    n = len(picks)
    # Khởi tạo
    plans = [
    DayPlan(day=day, activity=act, minutes=minutes_low,
            kcal=estimate_kcal_db(weight_kg, minutes_low, cpk),
            cpk_per_hour=cpk)
    for day, act, cpk in picks
]

    current_total = sum(p.kcal for p in plans)
    need = weekly_target_kcal - current_total

    if need <= 0:
        # Không thể giảm dưới minutes_low; thử đổi hoạt động ít MET hơn nếu chênh quá lớn (bỏ qua để đơn giản)
        return plans

    # Suất kcal per extra minute cho từng ngày
    per_min_rates = [cpk*weight_kg/60.0 for _,_,cpk in picks]
    # Chia thêm phút theo thứ tự rate giảm dần
    remaining_add = [minutes_high - minutes_low for _ in picks]
    order = sorted(range(n), key=lambda i: per_min_rates[i], reverse=True)

    for i in order:
        if need <= 0:
            break
        # phút cần để bù
        can_add = remaining_add[i]
        if can_add <= 0:
            continue
        # kcal/m cho ngày i
        r = per_min_rates[i]
        # số phút cần nếu bơm hết -> kcal thêm = r * can_add
        if r <= 0:
            continue
        minutes_needed = math.ceil(need / r)
        add_m = int(max(0, min(can_add, minutes_needed)))
        if add_m == 0 and need > 0:
            add_m = min(can_add, 1)  # bơm tối thiểu 1p nếu còn cần
        plans[i].minutes += add_m
        added_kcal = r * add_m
        plans[i].kcal += added_kcal
        need -= added_kcal
        remaining_add[i] -= add_m

    return plans

def make_weekly_plan(days: List[str], groups: List[str], weight_kg: float, weekly_target_kcal: float,
                     data_path: str | Path = "exercise_dataset (1).csv",
                     seed: int = 7) -> pd.DataFrame:
    random.seed(seed)

    # Chuẩn hoá ngày và sắp theo lịch trong tuần
    days_norm = [normalize_day_label(d) for d in days]
    order_map = {d: i for i, d in enumerate(VN_DAY_ORDER)}
    days_sorted = sorted(days_norm, key=lambda d: order_map.get(d, 99))

    # Load data và tạo pool theo nhóm
    df = load_activity_db(data_path)
    pool = build_pool_by_groups(df, groups, min_per_group=3)

    # Chọn hoạt động cho từng ngày (tránh 3 ngày liên tiếp trùng)
    picks = choose_activities_for_days(days_sorted, pool, weekly_target_kcal, weight_kg)

    # Phân bổ thời lượng 60–120 phút
    plans = allocate_durations(60, 120, picks, weight_kg, weekly_target_kcal)

    # --- Tạo DataFrame có đủ 7 ngày ---
    plan_records = []
    selected_days = [p.day for p in plans]

    for day in VN_DAY_ORDER:
        if day in selected_days:
            p = next(p for p in plans if p.day == day)
            plan_records.append({
                "Ngày": p.day,
                "Hoạt động": p.activity,
                "Thời gian (phút)": int(p.minutes),
                "Kcal ước tính": round(p.kcal, 1)
            })
        else:
            # Ngày nghỉ
            plan_records.append({
                "Ngày": day,
                "Hoạt động": "Rest",
                "Thời gian (phút)": 0,
                "Kcal ước tính": 0.0
            })

    out = pd.DataFrame(plan_records)
    out["Ngày"] = pd.Categorical(out["Ngày"], categories=VN_DAY_ORDER, ordered=True)
    out = out.sort_values("Ngày").reset_index(drop=True)

    total = out["Kcal ước tính"].sum()
    print(f"Tổng kcal ước tính = {total:.1f} (Target = {weekly_target_kcal:.1f}) | Sai lệch = {total - weekly_target_kcal:+.1f}")
    return out

def swap_days(plan_df: pd.DataFrame, day1: str, day2: str) -> pd.DataFrame:
    """Đổi cặp hoạt động giữa hai ngày (hoán đổi toàn bộ activity + minutes + kcal)."""
    d1 = normalize_day_label(day1)
    d2 = normalize_day_label(day2)
    df = plan_df.copy()
    i1 = df.index[df["Ngày"].str.lower()==d1].tolist()
    i2 = df.index[df["Ngày"].str.lower()==d2].tolist()
    if not i1 or not i2:
        print("[Cảnh báo] Không tìm thấy một trong hai ngày để swap.")
        return df
    i1, i2 = i1[0], i2[0]
    # Hoán đổi từng cột
    cols = ["Hoạt động","Thời gian (phút)","Kcal ước tính"]
    tmp = df.loc[i1, cols].copy()
    df.loc[i1, cols] = df.loc[i2, cols].values
    df.loc[i2, cols] = tmp.values
    return df

def change_activity(plan_df: pd.DataFrame, day: str, data_path: str, weight_kg: float) -> pd.DataFrame:
    """
    Tự động đổi hoạt động của 1 ngày sang hoạt động khác cùng nhóm,
    nhưng vẫn giữ nguyên lượng calo mong muốn bằng cách điều chỉnh thời gian.
    """
    d = normalize_day_label(day)
    df = plan_df.copy()
    idx = df.index[df["Ngày"].str.lower() == d].tolist()
    if not idx:
        print(f"[Lỗi] Không tìm thấy ngày {day} trong kế hoạch.")
        return df

    old_activity = df.loc[idx[0], "Hoạt động"]
    old_kcal = df.loc[idx[0], "Kcal ước tính"]
    if old_activity.lower() == "rest" or old_kcal == 0:
        print("[Lỗi] Ngày này là 'Rest' — không thể đổi hoạt động.")
        return df

    # Load database
    act_db = load_activity_db(data_path)
    act_db["groups"] = act_db["activity_lower"].apply(tag_group)

    # Xác định nhóm của hoạt động cũ
    old_info = act_db[act_db["activity"].str.lower() == old_activity.lower()]
    if old_info.empty:
        print(f"[Cảnh báo] Không xác định được nhóm của hoạt động cũ: {old_activity}")
        return df
    old_groups = old_info.iloc[0]["groups"]

    # Lấy danh sách hoạt động khác cùng nhóm
    same_group = act_db[
        act_db["groups"].apply(lambda g: any(gr in old_groups for gr in g))
        & (act_db["activity"] != old_activity)
    ]
    if same_group.empty:
        print(f"[Cảnh báo] Không tìm thấy hoạt động khác cùng nhóm với '{old_activity}'.")
        return df

    # Chọn ngẫu nhiên một hoạt động khác cùng nhóm
    new_row = same_group.sample(1).iloc[0]
    cpk = new_row["cpk_per_hour"]

    # Tính lại thời gian sao cho kcal mới ≈ kcal cũ
    # kcal = cpk * weight_kg * (minutes / 60)
    minutes_new = (old_kcal * 60) / (cpk * weight_kg)
    minutes_new = max(30, min(150, round(minutes_new, 1)))  # Giới hạn 30–150 phút

    kcal_new = estimate_kcal_db(weight_kg, minutes_new, cpk)

    # Cập nhật lại bảng
    df.loc[idx[0], "Hoạt động"] = new_row["activity"]
    df.loc[idx[0], "Thời gian (phút)"] = minutes_new
    df.loc[idx[0], "Kcal ước tính"] = round(kcal_new, 1)

    print(
        f"✅ Đã tự động đổi hoạt động của {day}: '{old_activity}' → '{new_row['activity']}' "
        f"(thời gian {minutes_new} phút ≈ {round(kcal_new,1)} kcal, giữ nguyên mức năng lượng mục tiêu)."
    )
    return df


