import pandas as pd
import joblib

MODEL_PATH = "artifacts/best_calorie_model.pkl"
model = joblib.load(MODEL_PATH)

\

def _age_group(age: float) -> str:
    """Group age to match trained categories."""
    if age <= 30: return "18-30"
    if age <= 45: return "31-45"
    if age <= 60: return "46-60"
    return "61+"


def make_feature_row(age, sex, height_cm, weight_kg, duration_min, heart_rate_bpm, body_temp_c=37.0):
    """Create a single-row DataFrame with all features required by the model."""
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
    """Predict burned calories."""
    X = make_feature_row(age, sex, height_cm, weight_kg, duration_min, heart_rate_bpm, body_temp_c)
    kcal = float(model.predict(X)[0])
    return max(0.0, kcal)


def what_if_predict(age, sex, height, weight, duration, heart_rate, body_temp):
    """
    Main function for What-if Coach.

    INPUT:
        age, sex, height, weight, duration, heart_rate, body_temp

    OUTPUT:
        {
            "predicted_kcal": float,
            "compare_duration": [ {scenario, calories}, ... ],
            "compare_heartrate": [ {scenario, calories}, ... ]
        }
    """
    # Main prediction
    kcal = predict_kcal(model, age, sex, height, weight, duration, heart_rate, body_temp)

    # Duration comparison
    duration_compares = []
    for d in [duration - 10, duration, duration + 10]:
        if d > 0:
            k = predict_kcal(model, age, sex, height, weight, d, heart_rate, body_temp)
            duration_compares.append({"scenario": f"{d} min", "calories": round(k, 1)})

    # Heart rate comparison
    hr_compares = []
    for hr in [heart_rate - 20, heart_rate, heart_rate + 20]:
        if 60 < hr < 200:
            k = predict_kcal(model, age, sex, height, weight, duration, hr, body_temp)
            hr_compares.append({"scenario": f"{hr} bpm", "calories": round(k, 1)})

    return {
        "predicted_kcal": round(kcal, 1),
        "compare_duration": duration_compares,
        "compare_heartrate": hr_compares
    }
