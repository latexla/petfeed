from unittest.mock import MagicMock

from app.services.ai_service import build_food_context


def make_cf(brand, name, kcal, life_stage="adult"):
    cf = MagicMock()
    cf.brand = brand; cf.name = name; cf.kcal_per_100g = kcal
    cf.life_stage = life_stage; cf.food_type = "dry"
    return cf


def test_build_food_context_compact():
    foods = [make_cf("Royal Canin", "Sterilised 37", 350),
             make_cf("Pro Plan", "Adult", 367)]
    ctx = build_food_context(foods)
    assert "Royal Canin Sterilised 37" in ctx
    assert "350" in ctx
    assert ctx.count("\n") <= 6  # stays compact


def test_build_food_context_empty():
    assert build_food_context([]) == ""
