import json
from unittest.mock import MagicMock

import pytest

from app.models.commercial_food import CommercialFood
from app.services.commercial_food_service import CommercialFoodService


def make_cf(brand, name, species="cat", food_type="dry", life_stage="adult",
            breed_size=None, tags=None, kcal=350, prot=37, fat=12, carb=30):
    cf = CommercialFood()
    cf.brand = brand; cf.name = name; cf.name_aliases = json.dumps([name.lower()])
    cf.species = species; cf.food_type = food_type; cf.life_stage = life_stage
    cf.breed_size = breed_size; cf.condition_tags = json.dumps(tags or [])
    cf.kcal_per_100g = kcal; cf.protein_g = prot; cf.fat_g = fat; cf.carb_g = carb
    return cf


def make_pet(species="cat", age_months=36, breed="", goal="maintain"):
    pet = MagicMock()
    pet.species = species; pet.age_months = age_months; pet.breed = breed; pet.goal = goal
    return pet


def test_life_stage_from_age_cat():
    svc = CommercialFoodService(repo=MagicMock())
    assert svc.life_stage_for(make_pet(species="cat", age_months=6)) == "junior"
    assert svc.life_stage_for(make_pet(species="cat", age_months=36)) == "adult"
    assert svc.life_stage_for(make_pet(species="cat", age_months=132)) == "senior"


def test_pet_to_filters_maps_goal_and_risks():
    svc = CommercialFoodService(repo=MagicMock())
    pet = make_pet(species="cat", age_months=36, goal="lose")
    f = svc.pet_to_filters(pet, breed_risks=["urinary"])
    assert f["species"] == "cat"
    assert f["life_stage"] == "adult"
    assert "weight_control" in f["tags"]
    assert "urinary" in f["tags"]


def test_rank_prefers_more_matching_axes():
    svc = CommercialFoodService(repo=MagicMock())
    a = make_cf("A", "match-all", life_stage="adult", tags=["weight_control"])
    b = make_cf("B", "partial", life_stage="all", tags=[])
    filters = {"species": "cat", "life_stage": "adult", "food_type": "dry",
               "breed_size": None, "tags": ["weight_control"]}
    ranked = svc.rank([b, a], filters)
    assert ranked[0].brand == "A"
