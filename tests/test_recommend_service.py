import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.recommend_service import RecommendService
from app.services.meal_service import FoodLookupResult, StopCheckResult


def _make_lookup(name: str, kcal: float, protein_g: float, fat_g: float,
                 carb_g: float = 0.0, calcium_mg: float = 100.0,
                 phosphorus_mg: float = 80.0, omega3_mg: float = 50.0,
                 taurine_mg: float = 0.0, food_item_id: int | None = None) -> FoodLookupResult:
    return FoodLookupResult(
        name=name, grams=0, kcal=kcal, protein_g=protein_g,
        fat_g=fat_g, carb_g=carb_g, calcium_mg=calcium_mg,
        phosphorus_mg=phosphorus_mg, omega3_mg=omega3_mg,
        taurine_mg=taurine_mg, source="db", food_item_id=food_item_id,
    )


def _make_pet(species: str = "dog", breed: str = "labrador",
              age_months: int = 24, weight_kg: float = 30.0):
    p = MagicMock()
    p.id = 1
    p.species = species
    p.breed = breed
    p.age_months = age_months
    p.weight_kg = weight_kg
    return p


def _make_ration(daily_calories: float = 1000.0, meals_per_day: int = 2):
    r = MagicMock()
    r.daily_calories = daily_calories
    r.meals_per_day = meals_per_day
    return r


def _make_meal_svc(lookups: dict):
    svc = MagicMock()
    svc.lookup_product = AsyncMock(side_effect=lambda name: lookups.get(name))
    svc.check_stop_list = MagicMock(
        return_value=StopCheckResult(None, None, None, None)
    )
    svc.get_required_micros = MagicMock(
        return_value=["omega3_mg", "calcium_mg", "phosphorus_mg"]
    )
    svc.compute_micro_targets = MagicMock(return_value={
        "omega3_mg": 250.0, "calcium_mg": 1250.0, "phosphorus_mg": 1000.0
    })
    svc.get_summary_tip = MagicMock(return_value="")
    svc.get_excess_warnings = MagicMock(return_value=[])
    # repo.get_stop_foods_for_species используется в recommend_natural
    svc.repo = MagicMock()
    svc.repo.get_stop_foods_for_species = AsyncMock(return_value=[])
    return svc


def _make_nutrition_repo(breed_risks: list[str] | None = None):
    repo = AsyncMock()
    repo.get_breed_risks = AsyncMock(return_value=breed_risks or [])
    repo.get_stop_foods = AsyncMock(return_value=[])
    return repo


@pytest.mark.asyncio
async def test_natural_distributes_calories_by_protein_weight():
    """Продукт с большим белком получает больше калорий."""
    lookups = {
        "курица": _make_lookup("курица", kcal=150.0, protein_g=25.0, fat_g=3.0, food_item_id=1),
        "гречка": _make_lookup("гречка", kcal=100.0, protein_g=3.0, fat_g=1.0, carb_g=20.0, food_item_id=2),
    }
    svc = RecommendService(_make_meal_svc(lookups), _make_nutrition_repo())
    result = await svc.recommend_natural(
        pet=_make_pet(), ration=_make_ration(daily_calories=500.0),
        ingredients=["курица", "гречка"],
    )
    assert len(result.items) == 2
    chicken = next(i for i in result.items if i.name == "курица")
    buckwheat = next(i for i in result.items if i.name == "гречка")
    assert chicken.kcal > buckwheat.kcal


@pytest.mark.asyncio
async def test_natural_excludes_fatal_stop_list_items():
    """Продукт с уровнем stop 1 (fatal) исключается из рекомендации."""
    lookups = {
        "шоколад": _make_lookup("шоколад", kcal=500.0, protein_g=5.0, fat_g=30.0),
        "курица":  _make_lookup("курица",  kcal=150.0, protein_g=25.0, fat_g=3.0, food_item_id=1),
    }
    meal_svc = _make_meal_svc(lookups)
    meal_svc.check_stop_list = MagicMock(
        side_effect=lambda name, stops: (
            StopCheckResult(1, name, "теобромин", "тахикардия")
            if name == "шоколад"
            else StopCheckResult(None, None, None, None)
        )
    )
    svc = RecommendService(meal_svc, _make_nutrition_repo())
    result = await svc.recommend_natural(
        pet=_make_pet(), ration=_make_ration(),
        ingredients=["шоколад", "курица"],
    )
    names = [i.name for i in result.items]
    assert "шоколад" not in names
    assert "курица" in names
    assert any("шоколад" in w.lower() for w in result.warnings)


@pytest.mark.asyncio
async def test_natural_skips_not_found_ingredient():
    """Ингредиент, которого нет в БД и DeepSeek, пропускается без ошибки."""
    lookups = {
        "курица": _make_lookup("курица", kcal=150.0, protein_g=25.0, fat_g=3.0, food_item_id=1),
        "загадочный продукт": None,
    }
    svc = RecommendService(_make_meal_svc(lookups), _make_nutrition_repo())
    result = await svc.recommend_natural(
        pet=_make_pet(), ration=_make_ration(),
        ingredients=["курица", "загадочный продукт"],
    )
    assert len(result.items) == 1
    assert result.items[0].name == "курица"


@pytest.mark.asyncio
async def test_commercial_calculates_daily_grams():
    """Суточные граммы = (daily_calories / kcal_per_100g) * 100."""
    lookups = {"Royal Canin Adult": _make_lookup(
        "Royal Canin Adult", kcal=360.0, protein_g=26.0, fat_g=16.0,
        carb_g=40.0, calcium_mg=1200.0, phosphorus_mg=950.0,
        omega3_mg=200.0, food_item_id=10,
    )}
    svc = RecommendService(_make_meal_svc(lookups), _make_nutrition_repo())
    result = await svc.recommend_commercial(
        pet=_make_pet(), ration=_make_ration(daily_calories=720.0),
        product_name="Royal Canin Adult",
    )
    assert len(result.items) == 1
    item = result.items[0]
    expected_grams = round((720.0 / 360.0) * 100, 1)
    assert abs(item.grams - expected_grams) < 1.0


@pytest.mark.asyncio
async def test_commercial_detects_taurine_deficiency_for_cat():
    """Для кошки с нехваткой таурина появляется дефицит."""
    lookups = {"Some Cat Food": _make_lookup(
        "Some Cat Food", kcal=350.0, protein_g=30.0, fat_g=12.0,
        carb_g=20.0, taurine_mg=0.0,
        calcium_mg=800.0, phosphorus_mg=700.0, omega3_mg=300.0,
        food_item_id=11,
    )}
    meal_svc = _make_meal_svc(lookups)
    meal_svc.get_required_micros = MagicMock(
        return_value=["taurine_mg", "omega3_mg", "calcium_mg", "phosphorus_mg"]
    )
    meal_svc.compute_micro_targets = MagicMock(return_value={
        "taurine_mg": 500.0, "omega3_mg": 400.0,
        "calcium_mg": 720.0, "phosphorus_mg": 640.0,
    })
    meal_svc.get_summary_tip = MagicMock(return_value="Не хватает таурина — обязателен для кошек")
    svc = RecommendService(meal_svc, _make_nutrition_repo())
    result = await svc.recommend_commercial(
        pet=_make_pet(species="cat"), ration=_make_ration(),
        product_name="Some Cat Food",
    )
    assert any("таурин" in d.lower() for d in result.deficiencies)


@pytest.mark.asyncio
async def test_covers_pct_reflects_calorie_coverage():
    """covers_pct отражает % покрытия суточной нормы калорий."""
    lookups = {"курица": _make_lookup("курица", kcal=200.0, protein_g=25.0, fat_g=3.0, food_item_id=1)}
    svc = RecommendService(_make_meal_svc(lookups), _make_nutrition_repo())
    result = await svc.recommend_natural(
        pet=_make_pet(), ration=_make_ration(daily_calories=1000.0),
        ingredients=["курица"],
    )
    expected = round(result.totals.kcal / 1000.0 * 100, 1)
    assert abs(result.covers_pct - expected) < 1.0
