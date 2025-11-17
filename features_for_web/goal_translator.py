from features_for_web.weekly_planner import UserProfile
from features_for_web.weekly_planner import weekly_plan_generator
from typing import Literal, Tuple, List, Optional
import pandas as pd

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
    """
    Chuyển đổi mục tiêu cân nặng -> mục tiêu kcal/tuần -> kế hoạch buổi tập.
    """
    # 1) Chuyển đổi kg -> kcal (1 kg ≈ 7700 kcal)
    weekly_target_kcal = abs(weight_change_kg_per_week) * 7700

    # 2) Gọi bộ sinh kế hoạch tuần
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