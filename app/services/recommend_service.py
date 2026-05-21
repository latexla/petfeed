from app.models.pet import Pet
from app.models.ration import Ration
from app.schemas.recommend import RecommendItem, RecommendResponse, NutrientMap
from app.services.meal_service import MealService
from app.repositories.nutrition_repo import NutritionRepository

_SUPPORTED_SPECIES = {"cat", "dog"}


class RecommendService:
    def __init__(self, meal_svc: MealService, nutrition_repo: NutritionRepository):
        self.meal_svc = meal_svc
        self.nutrition_repo = nutrition_repo

    async def recommend_natural(
        self, pet: Pet, ration: Ration, ingredients: list[str],
    ) -> RecommendResponse:
        breed_risks = await self.nutrition_repo.get_breed_risks(pet.breed or "")
        stop_foods = await self.nutrition_repo.get_stop_foods(pet.species, level=1)
        daily_calories = float(ration.daily_calories)

        lookups = {}
        warnings: list[str] = []

        for name in ingredients:
            result = await self.meal_svc.lookup_product(name)
            if result is None:
                warnings.append(f"Не удалось найти «{name}» — пропущен")
                continue
            stop = self.meal_svc.check_stop_list(name, stop_foods)
            if stop.level == 1:
                warnings.append(
                    f"⛔ «{stop.product_name}» нельзя — {stop.clinical_effect}. Исключён."
                )
                continue
            lookups[name] = result

        if not lookups:
            return RecommendResponse(
                items=[], totals=NutrientMap(), targets=NutrientMap(),
                micro_coverage={}, covers_pct=0.0,
                deficiencies=[], warnings=warnings,
            )

        proteins = {n: max(lu.protein_g, 0.1) for n, lu in lookups.items()}
        total_protein = sum(proteins.values())

        items: list[RecommendItem] = []
        for name, lu in lookups.items():
            allocated_kcal = daily_calories * (proteins[name] / total_protein)
            grams = round((allocated_kcal / lu.kcal) * 100, 1) if lu.kcal > 0 else 0.0
            factor = grams / 100
            items.append(RecommendItem(
                name=lu.name,
                grams=grams,
                kcal=round(lu.kcal * factor, 1),
                protein_g=round(lu.protein_g * factor, 1),
                fat_g=round(lu.fat_g * factor, 1),
                carb_g=round(lu.carb_g * factor, 1),
                calcium_mg=round(lu.calcium_mg * factor, 1),
                phosphorus_mg=round(lu.phosphorus_mg * factor, 1),
                omega3_mg=round(lu.omega3_mg * factor, 1),
                taurine_mg=round(lu.taurine_mg * factor, 1),
                food_item_id=lu.food_item_id,
            ))

        return self._build_response(items, pet, ration, breed_risks, warnings)

    async def recommend_commercial(
        self, pet: Pet, ration: Ration, product_name: str,
    ) -> RecommendResponse:
        breed_risks = await self.nutrition_repo.get_breed_risks(pet.breed or "")
        daily_calories = float(ration.daily_calories)

        lu = await self.meal_svc.lookup_product(product_name)
        if lu is None:
            return RecommendResponse(
                items=[], totals=NutrientMap(), targets=NutrientMap(),
                micro_coverage={}, covers_pct=0.0,
                deficiencies=[],
                warnings=[f"Не удалось найти «{product_name}». Попробуй другое название."],
            )

        grams = round((daily_calories / lu.kcal) * 100, 1) if lu.kcal > 0 else 0.0
        factor = grams / 100
        items = [RecommendItem(
            name=lu.name,
            grams=grams,
            kcal=round(lu.kcal * factor, 1),
            protein_g=round(lu.protein_g * factor, 1),
            fat_g=round(lu.fat_g * factor, 1),
            carb_g=round(lu.carb_g * factor, 1),
            calcium_mg=round(lu.calcium_mg * factor, 1),
            phosphorus_mg=round(lu.phosphorus_mg * factor, 1),
            omega3_mg=round(lu.omega3_mg * factor, 1),
            taurine_mg=round(lu.taurine_mg * factor, 1),
            food_item_id=lu.food_item_id,
        )]

        return self._build_response(items, pet, ration, breed_risks, [])

    def _build_response(
        self, items: list[RecommendItem], pet: Pet, ration: Ration,
        breed_risks: list[str], warnings: list[str],
    ) -> RecommendResponse:
        daily_calories = float(ration.daily_calories)

        totals_dict = {
            "kcal": sum(i.kcal for i in items),
            "protein_g": sum(i.protein_g for i in items),
            "fat_g": sum(i.fat_g for i in items),
            "carb_g": sum(i.carb_g for i in items),
            "calcium_mg": sum(i.calcium_mg for i in items),
            "phosphorus_mg": sum(i.phosphorus_mg for i in items),
            "omega3_mg": sum(i.omega3_mg for i in items),
            "taurine_mg": sum(i.taurine_mg for i in items),
        }
        totals = NutrientMap(**{k: round(v, 1) for k, v in totals_dict.items()})
        covers_pct = round(totals_dict["kcal"] / daily_calories * 100, 1) if daily_calories > 0 else 0.0

        micro_coverage: dict[str, float] = {}
        deficiencies: list[str] = []
        targets = NutrientMap()

        if pet.species in _SUPPORTED_SPECIES:
            required_micros = self.meal_svc.get_required_micros(pet.species, breed_risks)
            micro_targets = self.meal_svc.compute_micro_targets(
                mer=daily_calories,
                meals_per_day=1,
                species=pet.species,
                required_micros=required_micros,
            )
            daily_grams_est = daily_calories / 350 * 100
            pct_prot = 0.225 if pet.age_months < 12 else 0.18
            fat_pct_kcal = 0.25 if pet.age_months < 12 else 0.20
            full_targets = {
                "kcal": daily_calories,
                "protein_g": round(daily_grams_est * pct_prot, 1),
                "fat_g": round(daily_calories * fat_pct_kcal / 9, 1),
                **micro_targets,
            }
            targets = NutrientMap(**{
                k: round(v, 1) for k, v in full_targets.items()
                if k in NutrientMap.model_fields
            })
            for micro, tval in micro_targets.items():
                got = totals_dict.get(micro, 0)
                micro_coverage[micro] = round(got / tval * 100, 1) if tval > 0 else 0.0

            tip = self.meal_svc.get_summary_tip(totals_dict, full_targets, required_micros)
            if tip:
                deficiencies.append(tip)

            excess = self.meal_svc.get_excess_warnings(
                totals=totals_dict,
                target_kcal=daily_calories,
                species=pet.species,
                age_months=pet.age_months,
                weight_kg=float(pet.weight_kg),
            )
            warnings.extend(excess)

            ca = totals_dict.get("calcium_mg", 0)
            p = totals_dict.get("phosphorus_mg", 0)
            if p > 0 and (ca / p) < 1.2:
                warnings.append(f"⚠️ Ca:P = {ca/p:.2f}:1 — ниже нормы 1.2:1")

        return RecommendResponse(
            items=items,
            totals=totals,
            targets=targets,
            micro_coverage=micro_coverage,
            covers_pct=covers_pct,
            deficiencies=deficiencies,
            warnings=warnings,
        )
