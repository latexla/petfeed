from dataclasses import dataclass
from app.models.pet import Pet
from app.models.ration import Ration
from app.models.food_category import FoodCategory
from app.repositories.nutrition_repo import NutritionRepository


ACTIVITY_MULTIPLIER = {
    "low": 0.8,
    "moderate": 1.0,
    "high": 1.2,
    "working": 1.6,
}


class MERCalculator:
    def __init__(self, weight_kg: float, age_months: int, is_neutered: bool,
                 activity_level: str, physio_status: str, goal: str,
                 breed_risks: list[str]):
        self.weight_kg = weight_kg
        self.age_months = age_months
        self.is_neutered = is_neutered
        self.activity_level = activity_level
        self.physio_status = physio_status
        self.goal = goal
        self.breed_risks = breed_risks

    def rer(self) -> float:
        return 70 * (self.weight_kg ** 0.75)

    def _base_coefficient(self) -> float:
        if self.age_months < 4:
            return 3.0
        if self.age_months < 12:
            return 2.0
        if self.physio_status in ("pregnant", "lactating"):
            return 2.5
        if self.physio_status == "recovery":
            return 1.3
        if self.goal == "lose" or "obesity" in self.breed_risks:
            return 1.4
        if self.is_neutered:
            return 1.6
        return 1.8

    def mer(self) -> float:
        multiplier = ACTIVITY_MULTIPLIER.get(self.activity_level, 1.0)
        return self.rer() * self._base_coefficient() * multiplier

    def meals_per_day(self) -> int:
        if self.age_months < 4:
            return 5
        if self.age_months < 6:
            return 4
        if self.age_months < 12:
            return 3
        return 2

    def daily_food_grams(self, kcal_per_100g: float) -> float:
        return (self.mer() / kcal_per_100g) * 100

    def _is_puppy(self) -> bool:
        return self.age_months < 12 or self.physio_status in ("pregnant", "lactating")

    def protein_min_g(self, daily_food_grams: float) -> float:
        pct = 0.225 if self._is_puppy() else 0.18
        return daily_food_grams * pct

    def fat_min_g(self, daily_food_grams: float) -> float:
        pct = 0.085 if self._is_puppy() else 0.055
        return daily_food_grams * pct

    def has_hypoglycemia_risk(self) -> bool:
        return self.age_months < 4 and "hypoglycemia_puppies" in self.breed_risks

    def recommendations(self) -> list[str]:
        notes = []
        notes.append("При смене корма — переход 7–10 дней")
        notes.append("Рекомендуется миска-лабиринт")
        if "atopy" in self.breed_risks:
            notes.append("Омега-3 добавки полезны для кожи и шерсти (предрасположенность к атопии)")
        if "patellar_luxation" in self.breed_risks:
            notes.append("Глюкозамин + хондроитин + Омега-3 для суставов (пателлярная люксация)")
        if self.activity_level == "working":
            notes.append("Рабочая собака: потребность в калориях существенно выше стандарта")
        return notes


@dataclass
class RationResult:
    daily_calories: float
    daily_food_grams: float
    meals_per_day: int
    food_per_meal_grams: float
    protein_min_g: float
    fat_min_g: float
    stop_foods_level1: list[dict]
    stop_foods_level2: list[dict]
    stop_foods_level3: list[dict]
    recommendations: list[str]
    hypoglycemia_warning: bool
    notes: str
    ration: Ration


class NutritionService:
    def __init__(self, repo: NutritionRepository):
        self.repo = repo

    async def calculate_and_save(self, pet: Pet) -> RationResult:
        weight = float(pet.weight_kg)

        breed_risks = await self.repo.get_breed_risks(pet.breed or "")

        calc = MERCalculator(
            weight_kg=weight,
            age_months=pet.age_months,
            is_neutered=pet.is_neutered,
            activity_level=pet.activity_level,
            physio_status=pet.physio_status,
            goal=pet.goal,
            breed_risks=breed_risks,
        )

        food_cat: FoodCategory | None = None
        if pet.food_category_id:
            food_cat = await self.repo.get_food_category(pet.food_category_id)

        kcal_per_100g = float(food_cat.kcal_per_100g) if food_cat else 350.0

        mer = round(calc.mer(), 1)
        daily_grams = round(calc.daily_food_grams(kcal_per_100g), 1)
        meals = calc.meals_per_day()
        per_meal = round(daily_grams / meals, 1)
        protein_g = round(calc.protein_min_g(daily_grams), 1)
        fat_g = round(calc.fat_min_g(daily_grams), 1)

        stop1 = await self.repo.get_stop_foods(pet.species, level=1)
        stop2 = await self.repo.get_stop_foods(pet.species, level=2)
        stop3 = await self.repo.get_stop_foods(pet.species, level=3)

        ration = await self.repo.upsert_ration(
            pet_id=pet.id,
            daily_calories=mer,
            daily_food_grams=daily_grams,
            meals_per_day=meals,
            food_per_meal_grams=per_meal,
            notes="; ".join(calc.recommendations()),
        )

        return RationResult(
            daily_calories=mer,
            daily_food_grams=daily_grams,
            meals_per_day=meals,
            food_per_meal_grams=per_meal,
            protein_min_g=protein_g,
            fat_min_g=fat_g,
            stop_foods_level1=stop1,
            stop_foods_level2=stop2,
            stop_foods_level3=stop3,
            recommendations=calc.recommendations(),
            hypoglycemia_warning=calc.has_hypoglycemia_risk(),
            notes="; ".join(calc.recommendations()),
            ration=ration,
        )

    async def get_ration(self, pet_id: int) -> Ration | None:
        return await self.repo.get_ration_by_pet(pet_id)
