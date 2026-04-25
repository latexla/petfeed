import pytest
from app.services.nutrition_service import MERCalculator


class TestMERCalculator:

    def test_rer_formula(self):
        calc = MERCalculator(weight_kg=6.0, age_months=36,
                             is_neutered=False, activity_level="moderate",
                             physio_status="normal", goal="maintain",
                             breed_risks=[])
        assert round(calc.rer(), 1) == 268.4

    def test_adult_intact_moderate(self):
        calc = MERCalculator(weight_kg=6.0, age_months=36,
                             is_neutered=False, activity_level="moderate",
                             physio_status="normal", goal="maintain",
                             breed_risks=[])
        assert round(calc.mer(), 0) == 483

    def test_adult_neutered_moderate(self):
        calc = MERCalculator(weight_kg=6.0, age_months=36,
                             is_neutered=True, activity_level="moderate",
                             physio_status="normal", goal="maintain",
                             breed_risks=[])
        assert round(calc.mer(), 0) == 429

    def test_puppy_under_4mo(self):
        calc = MERCalculator(weight_kg=1.5, age_months=2,
                             is_neutered=False, activity_level="moderate",
                             physio_status="normal", goal="growth",
                             breed_risks=[])
        rer = 70 * (1.5 ** 0.75)
        assert round(calc.mer(), 1) == round(rer * 3.0, 1)

    def test_puppy_over_4mo(self):
        calc = MERCalculator(weight_kg=3.0, age_months=8,
                             is_neutered=False, activity_level="moderate",
                             physio_status="normal", goal="growth",
                             breed_risks=[])
        rer = 70 * (3.0 ** 0.75)
        assert round(calc.mer(), 1) == round(rer * 2.0, 1)

    def test_obesity_risk_lose_goal(self):
        calc = MERCalculator(weight_kg=6.0, age_months=36,
                             is_neutered=True, activity_level="moderate",
                             physio_status="normal", goal="lose",
                             breed_risks=["obesity"])
        assert round(calc.mer(), 0) == 376

    def test_working_activity_multiplier(self):
        calc = MERCalculator(weight_kg=6.0, age_months=36,
                             is_neutered=False, activity_level="working",
                             physio_status="normal", goal="maintain",
                             breed_risks=[])
        assert round(calc.mer(), 0) == 773

    def test_pregnant_status(self):
        calc = MERCalculator(weight_kg=5.0, age_months=24,
                             is_neutered=False, activity_level="moderate",
                             physio_status="pregnant", goal="maintain",
                             breed_risks=[])
        rer = 70 * (5.0 ** 0.75)
        assert round(calc.mer(), 1) == round(rer * 2.5, 1)

    def test_meals_per_day_puppy_young(self):
        calc = MERCalculator(weight_kg=1.0, age_months=2,
                             is_neutered=False, activity_level="moderate",
                             physio_status="normal", goal="growth",
                             breed_risks=[])
        assert calc.meals_per_day() == 5

    def test_meals_per_day_adult(self):
        calc = MERCalculator(weight_kg=6.0, age_months=24,
                             is_neutered=True, activity_level="moderate",
                             physio_status="normal", goal="maintain",
                             breed_risks=[])
        assert calc.meals_per_day() == 2

    def test_daily_food_grams(self):
        calc = MERCalculator(weight_kg=6.0, age_months=36,
                             is_neutered=False, activity_level="moderate",
                             physio_status="normal", goal="maintain",
                             breed_risks=[])
        grams = calc.daily_food_grams(kcal_per_100g=350.0)
        assert round(grams, 0) == 138

    def test_protein_min_adult(self):
        calc = MERCalculator(weight_kg=6.0, age_months=36,
                             is_neutered=False, activity_level="moderate",
                             physio_status="normal", goal="maintain",
                             breed_risks=[])
        assert round(calc.protein_min_g(daily_food_grams=140.0), 1) == 25.2

    def test_protein_min_puppy(self):
        calc = MERCalculator(weight_kg=3.0, age_months=6,
                             is_neutered=False, activity_level="moderate",
                             physio_status="normal", goal="growth",
                             breed_risks=[])
        grams = calc.daily_food_grams(kcal_per_100g=350.0)
        assert round(calc.protein_min_g(daily_food_grams=grams), 1) == round(grams * 0.225, 1)

    def test_hypoglycemia_warning(self):
        calc = MERCalculator(weight_kg=1.0, age_months=3,
                             is_neutered=False, activity_level="moderate",
                             physio_status="normal", goal="growth",
                             breed_risks=["hypoglycemia_puppies"])
        assert calc.has_hypoglycemia_risk() is True

    def test_no_hypoglycemia_adult(self):
        calc = MERCalculator(weight_kg=6.0, age_months=24,
                             is_neutered=False, activity_level="moderate",
                             physio_status="normal", goal="maintain",
                             breed_risks=[])
        assert calc.has_hypoglycemia_risk() is False
