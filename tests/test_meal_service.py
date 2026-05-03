import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.meal_service import MealService, RANGE_GUARD
from app.models.food_item import FoodItem
from app.models.stop_food import StopFood


def make_service() -> MealService:
    repo = AsyncMock()
    svc = MealService(repo)
    return svc


def make_food_item(name: str, aliases: list[str], category: str,
                   kcal: float, prot: float, fat: float, carb: float,
                   ca: float = 0, p: float = 0, omega: float = 0, tau: float = 0) -> FoodItem:
    fi = FoodItem()
    fi.name = name
    fi.name_aliases = json.dumps(aliases)
    fi.category = category
    fi.species = "all"
    fi.kcal_per_100g = kcal
    fi.protein_g = prot
    fi.fat_g = fat
    fi.carb_g = carb
    fi.calcium_mg = ca
    fi.phosphorus_mg = p
    fi.omega3_mg = omega
    fi.taurine_mg = tau
    return fi


def make_stop_food(name: str, level: int, species: str = "all",
                   toxic: str = "", effect: str = "") -> StopFood:
    sf = StopFood()
    sf.product_name = name
    sf.level = level
    sf.species = species
    sf.toxic_component = toxic
    sf.clinical_effect = effect
    return sf


class TestGetRequiredMicros:
    def test_dog_base(self):
        svc = make_service()
        micros = svc.get_required_micros("dog", [])
        assert "omega3_mg" in micros
        assert "calcium_mg" in micros
        assert "taurine_mg" not in micros

    def test_cat_has_taurine(self):
        svc = make_service()
        micros = svc.get_required_micros("cat", [])
        assert "taurine_mg" in micros

    def test_risk_boost_atopy(self):
        svc = make_service()
        micros = svc.get_required_micros("dog", ["atopy"])
        assert micros.count("omega3_mg") == 1


class TestCheckStopList:
    def test_level1_exact(self):
        svc = make_service()
        stops = [make_stop_food("виноград", 1, toxic="танины", effect="почечная недостаточность")]
        result = svc.check_stop_list("виноград", stops)
        assert result.level == 1
        assert result.toxic_component == "танины"

    def test_level1_fuzzy(self):
        svc = make_service()
        stops = [make_stop_food("виноград", 1)]
        result = svc.check_stop_list("виноградик", stops)
        assert result.level == 1

    def test_not_in_stoplist(self):
        svc = make_service()
        stops = [make_stop_food("виноград", 1)]
        result = svc.check_stop_list("курица", stops)
        assert result.level is None

    def test_level2(self):
        svc = make_service()
        stops = [make_stop_food("молоко", 2)]
        result = svc.check_stop_list("молоко", stops)
        assert result.level == 2


class TestSearchFoodItem:
    def test_exact_match(self):
        svc = make_service()
        chicken = make_food_item("курица варёная", ["курочка", "chicken"], "meat",
                                  165, 31, 3.6, 0)
        result = svc.search_food_item("курица", [chicken])
        assert result is not None
        assert result.name == "курица варёная"

    def test_alias_match(self):
        svc = make_service()
        chicken = make_food_item("курица варёная", ["курочка", "chicken"], "meat",
                                  165, 31, 3.6, 0)
        result = svc.search_food_item("курочка", [chicken])
        assert result is not None

    def test_no_match_below_threshold(self):
        svc = make_service()
        chicken = make_food_item("курица варёная", ["курочка"], "meat", 165, 31, 3.6, 0)
        result = svc.search_food_item("говядина", [chicken])
        assert result is None


class TestCalculateGrams:
    def test_clamp_min(self):
        svc = make_service()
        grams = svc.calculate_grams(gap_kcal=5, kcal_per_100g=165)
        assert grams == 20

    def test_clamp_max(self):
        svc = make_service()
        grams = svc.calculate_grams(gap_kcal=5000, kcal_per_100g=165)
        assert grams == 200

    def test_normal_case(self):
        svc = make_service()
        grams = svc.calculate_grams(gap_kcal=250, kcal_per_100g=165)
        assert 70 <= grams <= 80


class TestValidation:
    def test_range_guard_pass(self):
        svc = make_service()
        assert svc._validate_range("meat", 200) is True

    def test_range_guard_fail_high(self):
        svc = make_service()
        assert svc._validate_range("meat", 500) is False

    def test_range_guard_fail_low(self):
        svc = make_service()
        assert svc._validate_range("vegetable", 200) is False

    def test_math_guard_pass(self):
        svc = make_service()
        data = {"kcal": 165, "protein_g": 31, "fat_g": 3.6, "carb_g": 0}
        assert svc._validate_math(data) is True

    def test_math_guard_fail(self):
        svc = make_service()
        data = {"kcal": 500, "protein_g": 5, "fat_g": 1, "carb_g": 0}
        assert svc._validate_math(data) is False

    def test_math_guard_zero_kcal(self):
        svc = make_service()
        data = {"kcal": 0, "protein_g": 10, "fat_g": 1, "carb_g": 0}
        assert svc._validate_math(data) is False


class TestGetExcessWarnings:
    def _totals(self, kcal=300, ca=0, p=0, mg=0):
        return {
            "kcal": kcal,
            "calcium_mg": ca,
            "phosphorus_mg": p,
            "magnesium_mg": mg,
            "protein_g": 0, "fat_g": 0, "carb_g": 0,
            "omega3_mg": 0, "taurine_mg": 0,
        }

    def test_no_warnings_normal(self):
        svc = make_service()
        totals = self._totals(kcal=300, ca=375, p=300)  # 1250/1000/300 = within limits
        warnings = svc.get_excess_warnings(
            totals=totals, target_kcal=300,
            species="dog", age_months=24, weight_kg=20,
        )
        assert warnings == []

    def test_calcium_exceeded_dog_adult(self):
        svc = make_service()
        # 4500 mg/1000 kcal limit; 300 kcal meal → limit = 1350 mg
        totals = self._totals(kcal=300, ca=1400, p=300)
        warnings = svc.get_excess_warnings(
            totals=totals, target_kcal=300,
            species="dog", age_months=24, weight_kg=20,
        )
        assert any("Кальций" in w for w in warnings)

    def test_calcium_exceeded_large_breed_puppy(self):
        svc = make_service()
        # Puppy large breed: 2500 mg/1000 kcal; 300 kcal meal → limit = 750 mg
        totals = self._totals(kcal=300, ca=800, p=300)
        warnings = svc.get_excess_warnings(
            totals=totals, target_kcal=300,
            species="dog", age_months=6, weight_kg=20,
        )
        assert any("Кальций" in w for w in warnings)
        assert any("щенков крупных пород" in w for w in warnings)

    def test_calcium_ok_small_puppy(self):
        svc = make_service()
        # Small puppy (<15 kg) uses adult limit 4500 mg/1000 kcal
        totals = self._totals(kcal=300, ca=800, p=300)
        warnings = svc.get_excess_warnings(
            totals=totals, target_kcal=300,
            species="dog", age_months=6, weight_kg=5,
        )
        assert not any("Кальций" in w for w in warnings)

    def test_ca_p_ratio_exceeded(self):
        svc = make_service()
        # Ca:P = 3:1 > 2:1 max
        totals = self._totals(kcal=300, ca=900, p=300)
        warnings = svc.get_excess_warnings(
            totals=totals, target_kcal=300,
            species="dog", age_months=24, weight_kg=20,
        )
        assert any("Ca:P" in w for w in warnings)

    def test_magnesium_exceeded_cat(self):
        svc = make_service()
        # Cat Mg limit: 100 mg/1000 kcal; 300 kcal meal → limit = 30 mg
        totals = self._totals(kcal=300, ca=0, p=0, mg=50)
        warnings = svc.get_excess_warnings(
            totals=totals, target_kcal=300,
            species="cat", age_months=24, weight_kg=4,
        )
        assert any("Магний" in w for w in warnings)

    def test_magnesium_dog_not_flagged(self):
        svc = make_service()
        totals = self._totals(kcal=300, ca=0, p=0, mg=200)
        warnings = svc.get_excess_warnings(
            totals=totals, target_kcal=300,
            species="dog", age_months=24, weight_kg=20,
        )
        assert not any("Магний" in w for w in warnings)

    def test_calorie_excess_flagged(self):
        svc = make_service()
        totals = self._totals(kcal=400)  # target 300, excess = 33%
        warnings = svc.get_excess_warnings(
            totals=totals, target_kcal=300,
            species="dog", age_months=24, weight_kg=20,
        )
        assert any("Калорийность" in w for w in warnings)

    def test_calorie_within_20pct_ok(self):
        svc = make_service()
        totals = self._totals(kcal=350)  # target 300, excess = 16.7% < 20%
        warnings = svc.get_excess_warnings(
            totals=totals, target_kcal=300,
            species="dog", age_months=24, weight_kg=20,
        )
        assert not any("Калорийность" in w for w in warnings)

    def test_empty_totals_no_crash(self):
        svc = make_service()
        warnings = svc.get_excess_warnings(
            totals=self._totals(kcal=0), target_kcal=300,
            species="dog", age_months=24, weight_kg=20,
        )
        assert warnings == []

    # ── Macronutrient balance tests ────────────────────────────────────

    def _macro_totals(self, protein_g=0, fat_g=0, carb_g=0):
        kcal = protein_g * 4 + fat_g * 9 + carb_g * 4
        return {
            "kcal": kcal,
            "protein_g": protein_g, "fat_g": fat_g, "carb_g": carb_g,
            "calcium_mg": 0, "phosphorus_mg": 0,
            "magnesium_mg": 0, "omega3_mg": 0, "taurine_mg": 0,
        }

    def test_fat_warning_dog(self):
        svc = make_service()
        # 50g fat → 450 kcal; 20g protein → 80 kcal; total 530 kcal; fat = 85% ME
        totals = self._macro_totals(protein_g=20, fat_g=50, carb_g=0)
        warnings = svc.get_excess_warnings(
            totals=totals, target_kcal=totals["kcal"],
            species="dog", age_months=24, weight_kg=20,
        )
        assert any("Жир" in w for w in warnings)

    def test_fat_critical_dog(self):
        svc = make_service()
        # 80g fat → 720 kcal; 10g protein → 40 kcal; fat = 94.7% ME → above 55% stop
        totals = self._macro_totals(protein_g=10, fat_g=80, carb_g=0)
        warnings = svc.get_excess_warnings(
            totals=totals, target_kcal=totals["kcal"],
            species="dog", age_months=24, weight_kg=20,
        )
        assert any("🔴" in w and "Жир" in w for w in warnings)

    def test_fat_ok_dog(self):
        svc = make_service()
        # 30g fat → 270 kcal; 40g protein → 160 kcal; 30g carb → 120 kcal; total 550; fat=49%
        # Wait, 49% is above 40% warn. Let me use 20g fat
        # 20g fat → 180 kcal; 40g protein → 160 kcal; 30g carb → 120 kcal; total 460; fat=39%
        totals = self._macro_totals(protein_g=40, fat_g=20, carb_g=30)
        warnings = svc.get_excess_warnings(
            totals=totals, target_kcal=totals["kcal"],
            species="dog", age_months=24, weight_kg=20,
        )
        assert not any("Жир" in w for w in warnings)

    def test_carb_warning_cat(self):
        svc = make_service()
        # 5g fat → 45 kcal; 10g protein → 40 kcal; 60g carb → 240 kcal; total 325; carb=73.8%
        totals = self._macro_totals(protein_g=10, fat_g=5, carb_g=60)
        warnings = svc.get_excess_warnings(
            totals=totals, target_kcal=totals["kcal"],
            species="cat", age_months=24, weight_kg=4,
        )
        assert any("Углеводы" in w for w in warnings)
        assert any("кошек" in w for w in warnings)

    def test_carb_warning_dog_threshold_higher(self):
        svc = make_service()
        # Same 73% carb — should NOT warn for dog (threshold is 65%)
        # Let's use something clearly above 65% for dog
        # 5g protein → 20 kcal; 5g fat → 45 kcal; 70g carb → 280 kcal; total 345; carb=81%
        totals = self._macro_totals(protein_g=5, fat_g=5, carb_g=70)
        warnings = svc.get_excess_warnings(
            totals=totals, target_kcal=totals["kcal"],
            species="dog", age_months=24, weight_kg=20,
        )
        assert any("Углеводы" in w for w in warnings)
        assert not any("кошек" in w for w in warnings)

    def test_protein_warning_dog(self):
        svc = make_service()
        # 100g protein → 400 kcal; 5g fat → 45 kcal; total 445 kcal; protein=89.9%
        totals = self._macro_totals(protein_g=100, fat_g=5, carb_g=0)
        warnings = svc.get_excess_warnings(
            totals=totals, target_kcal=totals["kcal"],
            species="dog", age_months=24, weight_kg=20,
        )
        assert any("Белок" in w for w in warnings)

    def test_balanced_meal_no_macro_warnings(self):
        svc = make_service()
        # 30g protein → 120 kcal (39%); 12g fat → 108 kcal (35%); 20g carb → 80 kcal (26%); total 308
        totals = self._macro_totals(protein_g=30, fat_g=12, carb_g=20)
        warnings = svc.get_excess_warnings(
            totals=totals, target_kcal=totals["kcal"],
            species="dog", age_months=24, weight_kg=20,
        )
        macro_warns = [w for w in warnings if any(k in w for k in ("Белок", "Жир", "Углеводы"))]
        assert macro_warns == []


class TestIsDone:
    def test_done_when_90pct(self):
        svc = make_service()
        items = [{"kcal": 230, "protein_g": 28, "fat_g": 8, "carb_g": 10,
                  "calcium_mg": 0, "phosphorus_mg": 0, "omega3_mg": 0, "taurine_mg": 0}]
        target = {"kcal": 250, "protein_g": 30, "fat_g": 8}
        assert svc.is_done(items, target) is True

    def test_not_done_when_60pct(self):
        svc = make_service()
        items = [{"kcal": 150, "protein_g": 15, "fat_g": 4, "carb_g": 0,
                  "calcium_mg": 0, "phosphorus_mg": 0, "omega3_mg": 0, "taurine_mg": 0}]
        target = {"kcal": 250, "protein_g": 30, "fat_g": 8}
        assert svc.is_done(items, target) is False
