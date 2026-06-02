import json

from rapidfuzz import fuzz
from rapidfuzz import process as fuzz_process

from app.models.commercial_food import CommercialFood
from app.repositories.commercial_food_repo import CommercialFoodRepository

# Age thresholds (months): below junior_max -> junior; at/above senior_min -> senior.
LIFE_STAGE_THRESHOLDS = {
    "cat": (12, 120),
    "dog": (12, 96),
}
GOAL_TAGS = {"lose": "weight_control", "gain": "weight_gain"}


class CommercialFoodService:
    def __init__(self, repo: CommercialFoodRepository):
        self.repo = repo

    def life_stage_for(self, pet) -> str:
        junior_max, senior_min = LIFE_STAGE_THRESHOLDS.get(pet.species, (12, 120))
        if pet.age_months < junior_max:
            return "junior"
        if pet.age_months >= senior_min:
            return "senior"
        return "adult"

    def pet_to_filters(self, pet, breed_risks: list[str]) -> dict:
        tags: list[str] = []
        goal = getattr(pet, "goal", None)
        if goal in GOAL_TAGS:
            tags.append(GOAL_TAGS[goal])
        for risk in breed_risks:
            if risk in ("urinary", "renal", "sensitive", "obesity"):
                tags.append("weight_control" if risk == "obesity" else risk)
        return {
            "species": pet.species,
            "life_stage": self.life_stage_for(pet),
            "food_type": None,
            "breed_size": None,
            "tags": list(dict.fromkeys(tags)),  # dedup, keep order
        }

    def _axes_score(self, cf: CommercialFood, filters: dict) -> int:
        score = 0
        if filters.get("life_stage") and cf.life_stage in (filters["life_stage"], "all"):
            score += 1
        if filters.get("food_type") and cf.food_type == filters["food_type"]:
            score += 1
        if filters.get("breed_size") and cf.breed_size in (filters["breed_size"], "all", None):
            score += 1
        cf_tags = json.loads(cf.condition_tags or "[]")
        score += len(set(filters.get("tags", [])) & set(cf_tags))
        return score

    def rank(self, foods: list[CommercialFood], filters: dict) -> list[CommercialFood]:
        return sorted(foods, key=lambda cf: self._axes_score(cf, filters), reverse=True)

    async def find_for_lookup(self, product_name: str) -> CommercialFood | None:
        """Fuzzy match a free-text product name against name/aliases/brand."""
        foods = await self.repo.get_all()
        corpus: list[tuple[str, CommercialFood]] = []
        for cf in foods:
            corpus.append((f"{cf.brand} {cf.name}", cf))
            corpus.append((cf.name, cf))
            for alias in json.loads(cf.name_aliases or "[]"):
                corpus.append((alias, cf))
        if not corpus:
            return None
        texts = [c[0] for c in corpus]
        match = fuzz_process.extractOne(
            product_name, texts, scorer=fuzz.WRatio, score_cutoff=80
        )
        if match is None:
            return None
        return corpus[texts.index(match[0])][1]
