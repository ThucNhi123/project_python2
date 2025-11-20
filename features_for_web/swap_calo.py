import pandas as pd
import joblib

MODEL_PATH = "artifacts/best_calorie_model.pkl"
model = joblib.load(MODEL_PATH)

FOOD_DB_PATH = "data/food_calories_vi.csv"

def load_food_database():
    df = pd.read_csv(FOOD_DB_PATH)
    df["key"] = df["Food_Name"].str.lower().str.strip()
    return df

food_db = load_food_database()


def _age_group(age: float) -> str:
    if age <= 30: return "18-30"
    if age <= 45: return "31-45"
    if age <= 60: return "46-60"
    return "61+"


def make_feature_row(age, sex, height_cm, weight_kg, duration_min, heart_rate_bpm, body_temp_c=37.0):
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
        "Sex": sex
    }
    return pd.DataFrame([row])


def predict_kcal(model, age, sex, height_cm, weight_kg, duration_min, heart_rate_bpm, body_temp_c=37.0):
    X = make_feature_row(age, sex, height_cm, weight_kg, duration_min, heart_rate_bpm, body_temp_c)
    kcal = float(model.predict(X)[0])
    return max(0.0, kcal)



def solve_duration_for_target(model, target_kcal, age, sex, height_cm, weight_kg,
                              base_hr, max_minutes=120, body_temp_c=37.0,
                              tol=0.5, max_iter=40):

    lo, hi = 0.0, max_minutes
    kcal_hi = predict_kcal(model, age, sex, height_cm, weight_kg, hi, base_hr, body_temp_c)

    if kcal_hi + tol < target_kcal:
        return hi, kcal_hi, False

    for _ in range(max_iter):
        mid = (lo + hi) / 2
        kcal_mid = predict_kcal(model, age, sex, height_cm, weight_kg, mid, base_hr, body_temp_c)

        if abs(kcal_mid - target_kcal) <= tol:
            return mid, kcal_mid, True

        if kcal_mid < target_kcal:
            lo = mid
        else:
            hi = mid

    return hi, predict_kcal(model, age, sex, height_cm, weight_kg, hi, base_hr, body_temp_c), True


def swap_calories(food_name, quantity,
                  age, sex, height, weight,
                  base_hr, max_min, body_temp):
    """
    INPUT:
        food_name: tên món ăn (string)
        quantity: số lượng (int)
        age, sex, height, weight, base_hr, max_min

    OUTPUT:
        {
            "food_name": ...,
            "quantity": ...,
            "food_kcal": ...,
            "required_minutes": ...,
            "burn_estimate": ...,
            "feasible": bool
        }
    """

    key = food_name.lower().strip()
    row = food_db.loc[food_db["key"] == key]

    if row.empty:
        raise ValueError(f"Food '{food_name}' not found in CSV file.")

    kcal_per = float(row.iloc[0]["Calories_per_serving"])
    total_kcal = kcal_per * quantity

   
    dur, kcal_est, feasible = solve_duration_for_target(
        model, total_kcal, age, sex, height, weight, base_hr, max_min, body_temp
    )

    return {
        "food_name": food_name,
        "quantity": quantity,
        "food_kcal": total_kcal,
        "required_minutes": round(dur, 1),
        "burn_estimate": round(kcal_est, 1),
        "feasible": feasible
    }
