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

    # ── Cat-specific MER coefficients (NRC 2006) ────────────────────

    def _cat(self, **kw) -> MERCalculator:
        defaults = dict(weight_kg=4.0, age_months=24, is_neutered=False,
                        activity_level="moderate", physio_status="normal",
                        goal="maintain", breed_risks=[], species="cat")
        defaults.update(kw)
        return MERCalculator(**defaults)

    def test_cat_intact_adult_lower_than_dog(self):
        # Cat intact adult: 1.4 × RER; dog intact: 1.8 × RER
        cat = self._cat(is_neutered=False)
        dog = MERCalculator(weight_kg=4.0, age_months=24, is_neutered=False,
                            activity_level="moderate", physio_status="normal",
                            goal="maintain", breed_risks=[], species="dog")
        assert cat.mer() < dog.mer()

    def test_cat_intact_coefficient(self):
        # 4 kg cat, intact, moderate → RER * 1.4 * 1.0
        calc = self._cat(is_neutered=False)
        rer = 70 * (4.0 ** 0.75)
        assert round(calc.mer(), 1) == round(rer * 1.4, 1)

    def test_cat_neutered_coefficient(self):
        # 4 kg cat, neutered, moderate → RER * 1.2 * 1.0
        calc = self._cat(is_neutered=True)
        rer = 70 * (4.0 ** 0.75)
        assert round(calc.mer(), 1) == round(rer * 1.2, 1)

    def test_cat_weight_loss_coefficient(self):
        # Cat on weight loss: 0.8 × RER (not 1.4 like dogs)
        calc = self._cat(is_neutered=True, goal="lose")
        rer = 70 * (4.0 ** 0.75)
        assert round(calc.mer(), 1) == round(rer * 0.8, 1)

    def test_cat_sphynx_high_caloric_need(self):
        # Sphynx (high_caloric_need) intact: 1.8 × RER — same for cat/dog
        calc = self._cat(is_neutered=False, breed_risks=["high_caloric_need"])
        rer = 70 * (4.0 ** 0.75)
        assert round(calc.mer(), 1) == round(rer * 1.8, 1)

    def test_cat_protein_min_higher_than_dog(self):
        # Cats need more protein: 26% DM vs 18% DM for dogs
        cat = self._cat()
        dog = MERCalculator(weight_kg=4.0, age_months=24, is_neutered=False,
                            activity_level="moderate", physio_status="normal",
                            goal="maintain", breed_risks=[], species="dog")
        assert cat.protein_min_g(100.0) > dog.protein_min_g(100.0)

    def test_slow_maturation_growth_until_18mo(self):
        # Maine Coon at 14 months should still use growth coefficient (2.0)
        calc = MERCalculator(weight_kg=5.0, age_months=14, is_neutered=False,
                             activity_level="moderate", physio_status="normal",
                             goal="growth", breed_risks=["slow_maturation"],
                             species="cat")
        rer = 70 * (5.0 ** 0.75)
        assert round(calc.mer(), 1) == round(rer * 2.0, 1)

    def test_slow_maturation_adult_after_18mo(self):
        # Maine Coon at 20 months should use adult coefficient
        calc = MERCalculator(weight_kg=6.0, age_months=20, is_neutered=True,
                             activity_level="moderate", physio_status="normal",
                             goal="maintain", breed_risks=["slow_maturation"],
                             species="cat")
        rer = 70 * (6.0 ** 0.75)
        assert round(calc.mer(), 1) == round(rer * 1.2, 1)
