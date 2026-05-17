from unittest.mock import MagicMock
import pytest
from app.services.meal_service import MealService
from app.repositories.meal_repo import MealRepository


def make_svc():
    repo = MagicMock(spec=MealRepository)
    return MealService(repo)


def test_score_ratio_optimal():
    svc = make_svc()
    score, tips = svc._score_ratio(1.0, "калорий", "мало", "много")
    assert score == 100
    assert tips == []


def test_score_ratio_slightly_low():
    svc = make_svc()
    score, tips = svc._score_ratio(0.82, "белка", "мало белка", "много белка")
    assert score == 70
    assert len(tips) == 1


def test_score_ratio_low():
    svc = make_svc()
    score, tips = svc._score_ratio(0.6, "белка", "мало белка", "много белка")
    assert score == 40
    assert "мало белка" in tips[0]


def test_score_ratio_critical_low():
    svc = make_svc()
    score, tips = svc._score_ratio(0.3, "таурина", "мало таурина", "много таурина")
    assert score == 0
    assert any("критически" in t.lower() for t in tips)


def test_score_ratio_slightly_high():
    svc = make_svc()
    score, tips = svc._score_ratio(1.2, "калорий", "мало", "перекормил")
    assert score == 70
    assert len(tips) == 1


def test_score_ratio_critical_high():
    svc = make_svc()
    score, tips = svc._score_ratio(4.0, "кальция", "мало", "много", upper_hard=3.0)
    assert score == 0
    assert any("опасный" in t.lower() for t in tips)


def test_compute_quality_perfect_cat():
    svc = make_svc()
    daily_target = {"kcal": 320.0, "protein_g": 50.0, "fat_g": 20.0, "taurine_mg": 160.0, "omega3_mg": 128.0, "calcium_mg": 230.4, "phosphorus_mg": 204.8}
    totals = {"kcal": 310.0, "protein_g": 48.0, "fat_g": 21.0, "taurine_mg": 155.0, "omega3_mg": 125.0, "calcium_mg": 225.0, "phosphorus_mg": 200.0}
    score, quality, tips = svc.compute_quality(
        totals=totals, daily_target=daily_target,
        pet_species="cat", breed_risks=[], age_months=24, weight_kg=4.0,
    )
    assert quality == "good"
    assert score >= 80


def test_compute_quality_underfed():
    svc = make_svc()
    daily_target = {"kcal": 320.0, "protein_g": 50.0, "fat_g": 20.0}
    totals = {"kcal": 150.0, "protein_g": 20.0, "fat_g": 8.0}
    score, quality, tips = svc.compute_quality(
        totals=totals, daily_target=daily_target,
        pet_species="dog", breed_risks=[], age_months=24, weight_kg=10.0,
    )
    assert quality == "poor"
    assert score < 50
    assert any("мало" in t.lower() or "недоел" in t.lower() for t in tips)


def test_compute_quality_overfed():
    svc = make_svc()
    daily_target = {"kcal": 320.0, "protein_g": 50.0, "fat_g": 20.0}
    totals = {"kcal": 520.0, "protein_g": 95.0, "fat_g": 55.0}
    score, quality, tips = svc.compute_quality(
        totals=totals, daily_target=daily_target,
        pet_species="dog", breed_risks=[], age_months=24, weight_kg=10.0,
    )
    assert quality in ("ok", "poor")
    assert any("перекормил" in t.lower() or "много" in t.lower() for t in tips)


def test_compute_quality_empty_totals():
    svc = make_svc()
    score, quality, tips = svc.compute_quality(
        totals={}, daily_target={"kcal": 300.0},
        pet_species="cat", breed_risks=[], age_months=12, weight_kg=3.5,
    )
    assert isinstance(score, int)
    assert quality in ("good", "ok", "poor")
