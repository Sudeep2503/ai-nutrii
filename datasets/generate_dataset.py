import os
import random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "datasets" / "nutritional_deficiencies.csv"


def generate_dataset(output_path: str | None = None) -> pd.DataFrame:
    if output_path is None:
        output_path = str(OUTPUT_PATH)

    random.seed(42)
    rows = []
    deficiency_types = [
        "Iron Deficiency",
        "Vitamin D Deficiency",
        "Vitamin B12 Deficiency",
        "Calcium Deficiency",
        "Protein Deficiency",
        "Zinc Deficiency",
        "Magnesium Deficiency",
        "Vitamin A Deficiency",
    ]

    for index in range(1200):
        age = random.randint(18, 80)
        gender = random.choice(["Male", "Female", "Prefer not to say"])
        height = random.randint(150, 190)
        weight = max(45, int(height * 0.55 + random.randint(-20, 20)))
        activity_level = random.choice(["sedentary", "light", "moderate", "active", "very_active"])
        sleep_hours = round(random.uniform(5.5, 9.0), 1)
        water_intake = random.randint(1, 4)
        sunlight_exposure = random.randint(0, 3)
        diet_type = random.choice(["vegetarian", "vegan", "omnivore", "pescatarian"])
        meal_frequency = random.randint(1, 5)
        fruit_intake = random.randint(0, 4)
        vegetable_intake = random.randint(0, 4)
        dairy_intake = random.randint(0, 4)
        protein_intake = random.randint(0, 4)
        fast_food_frequency = random.randint(0, 4)
        sugary_drink_consumption = random.randint(0, 4)
        smoking = random.choice([0, 1])
        alcohol = random.choice([0, 1])

        symptoms = {
            "fatigue": random.choice([0, 1]),
            "weakness": random.choice([0, 1]),
            "hair_loss": random.choice([0, 1]),
            "pale_skin": random.choice([0, 1]),
            "muscle_cramps": random.choice([0, 1]),
            "bone_pain": random.choice([0, 1]),
            "frequent_illness": random.choice([0, 1]),
            "headaches": random.choice([0, 1]),
            "poor_concentration": random.choice([0, 1]),
            "tingling_sensation": random.choice([0, 1]),
        }

        deficiency = random.choice(deficiency_types)

        if deficiency == "Iron Deficiency":
            symptoms["fatigue"] = 1
            symptoms["pale_skin"] = 1
            symptoms["weakness"] = 1
            symptoms["headaches"] = 1
            symptoms["poor_concentration"] = 1
            if diet_type == "vegan":
                protein_intake = max(0, protein_intake - 1)
        elif deficiency == "Vitamin D Deficiency":
            symptoms["fatigue"] = 1
            symptoms["bone_pain"] = 1
            symptoms["weakness"] = 1
            sunlight_exposure = 0
        elif deficiency == "Vitamin B12 Deficiency":
            symptoms["fatigue"] = 1
            symptoms["tingling_sensation"] = 1
            symptoms["poor_concentration"] = 1
            if diet_type == "vegan":
                protein_intake = max(0, protein_intake - 1)
        elif deficiency == "Calcium Deficiency":
            symptoms["bone_pain"] = 1
            symptoms["muscle_cramps"] = 1
            symptoms["frequent_illness"] = 1
            dairy_intake = max(0, dairy_intake - 2)
        elif deficiency == "Protein Deficiency":
            symptoms["weakness"] = 1
            symptoms["muscle_cramps"] = 1
            symptoms["fatigue"] = 1
            protein_intake = max(0, protein_intake - 2)
        elif deficiency == "Zinc Deficiency":
            symptoms["hair_loss"] = 1
            symptoms["frequent_illness"] = 1
            symptoms["poor_concentration"] = 1
            diet_type = random.choice(["vegan", "vegetarian"])
        elif deficiency == "Magnesium Deficiency":
            symptoms["muscle_cramps"] = 1
            symptoms["fatigue"] = 1
            symptoms["headaches"] = 1
            sleep_hours = max(4.0, sleep_hours - 1.5)
        elif deficiency == "Vitamin A Deficiency":
            symptoms["frequent_illness"] = 1
            symptoms["poor_concentration"] = 1
            symptoms["hair_loss"] = 1
            fruit_intake = max(0, fruit_intake - 1)
            vegetable_intake = max(0, vegetable_intake - 1)

        rows.append(
            {
                "age": age,
                "gender": gender,
                "height": height,
                "weight": weight,
                "activity_level": activity_level,
                "sleep_hours": sleep_hours,
                "water_intake": water_intake,
                "sunlight_exposure": sunlight_exposure,
                "diet_type": diet_type,
                "meal_frequency": meal_frequency,
                "fruit_intake": fruit_intake,
                "vegetable_intake": vegetable_intake,
                "dairy_intake": dairy_intake,
                "protein_intake": protein_intake,
                "fast_food_frequency": fast_food_frequency,
                "sugary_drink_consumption": sugary_drink_consumption,
                "smoking": smoking,
                "alcohol": alcohol,
                **symptoms,
                "deficiency": deficiency,
            }
        )

    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


if __name__ == "__main__":
    generate_dataset()
    print(f"Dataset created at {OUTPUT_PATH}")
