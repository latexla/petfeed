import json
import logging
from dataclasses import dataclass
from rapidfuzz import process as fuzz_process, fuzz
from openai import AsyncOpenAI
from app.config import settings
from app.models.food_item import FoodItem
from app.models.stop_food import StopFood
from app.repositories.meal_repo import MealRepository

logger = logging.getLogger(__name__)

SPECIES_MICROS: dict[str, list[str]] = {
    "cat":     ["taurine_mg", "omega3_mg", "calcium_mg", "phosphorus_mg"],
    "dog":     ["omega3_mg", "calcium_mg", "phosphorus_mg"],
    "rodent":  ["calcium_mg", "phosphorus_mg"],
    "bird":    ["calcium_mg"],
    "reptile": ["calcium_mg", "phosphorus_mg"],
}
RISK_BOOST: dict[str, list[str]] = {
    "atopy":             ["omega3_mg"],
    "patellar_luxation": ["omega3_mg"],
}
RANGE_GUARD: dict[str, tuple[float, float]] = {
    "meat":      (80, 400),
    "fish":      (80, 300),
    "egg":       (130, 160),
    "grain":     (60, 380),
    "vegetable": (15, 100),
    "dairy":     (30, 400),
    "oil":       (700, 900),
}
# Minimum nutrients per 1000 kcal (NRC 2006)
MICRO_PER_1000KCAL: dict[str, dict[str, float]] = {
    "dog":  {"calcium_mg": 1250, "phosphorus_mg": 1000, "omega3_mg": 110},
    "cat":  {"taurine_mg": 500,  "omega3_mg": 110, "calcium_mg": 720, "phosphorus_mg": 640},
}
EXAMPLES_BY_TYPE: dict[str, str] = {
    "natural":  "курица, говядина, гречка, морковь, яйцо",
    "prepared": "Royal Canin, Purina Pro Plan, Hills",
    "mixed":    "курица + гречка + сухой корм",
}


@dataclass
class StopCheckResult:
    level: int | None
    product_name: str | None
    toxic_component: str | None
    clinical_effect: str | None


@dataclass
class FoodLookupResult:
    name: str
    grams: float
    kcal: float
    protein_g: float
    fat_g: float
    carb_g: float
    calcium_mg: float
    phosphorus_mg: float
    omega3_mg: float
    taurine_mg: float
    source: str
    confidence: float = 1.0
    low_confidence: bool = False


class MealService:
    def __init__(self, repo: MealRepository):
        self.repo = repo
        self._deepseek = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
        )

    # ── Public API ──────────────────────────────────────────────────

    def get_required_micros(self, species: str, breed_risks: list[str]) -> list[str]:
        micros = list(SPECIES_MICROS.get(species, ["calcium_mg", "phosphorus_mg"]))
        for risk in breed_risks:
            for extra in RISK_BOOST.get(risk, []):
                if extra not in micros:
                    micros.append(extra)
        return micros

    def compute_micro_targets(self, mer: float, meals_per_day: int,
                               species: str, required_micros: list[str]) -> dict:
        per_1000 = MICRO_PER_1000KCAL.get(species, {})
        targets = {}
        for micro in required_micros:
            if micro in per_1000:
                targets[micro] = round(per_1000[micro] * mer / 1000 / meals_per_day, 1)
        return targets

    def check_stop_list(self, product_name: str,
                        stop_foods: list[StopFood]) -> StopCheckResult:
        names = [sf.product_name for sf in stop_foods]
        match = fuzz_process.extractOne(
            product_name, names,
            scorer=fuzz.WRatio,
            score_cutoff=75,
        )
        if match is None:
            return StopCheckResult(None, None, None, None)
        idx = names.index(match[0])
        sf = stop_foods[idx]
        return StopCheckResult(
            level=sf.level,
            product_name=sf.product_name,
            toxic_component=sf.toxic_component,
            clinical_effect=sf.clinical_effect,
        )

    def search_food_item(self, product_name: str,
                         food_items: list[FoodItem]) -> FoodItem | None:
        corpus: list[tuple[str, FoodItem]] = []
        for fi in food_items:
            corpus.append((fi.name, fi))
            if fi.name_aliases:
                try:
                    aliases = json.loads(fi.name_aliases)
                    for alias in aliases:
                        corpus.append((alias, fi))
                except (json.JSONDecodeError, TypeError):
                    pass

        texts = [c[0] for c in corpus]
        match = fuzz_process.extractOne(
            product_name, texts,
            scorer=fuzz.WRatio,
            score_cutoff=80,
        )
        if match is None:
            return None
        idx = texts.index(match[0])
        return corpus[idx][1]

    async def lookup_product(self, product_name: str) -> FoodLookupResult | None:
        food_items = await self.repo.get_all_food_items()
        fi = self.search_food_item(product_name, food_items)
        if fi:
            return FoodLookupResult(
                name=fi.name, grams=0,
                kcal=float(fi.kcal_per_100g),
                protein_g=float(fi.protein_g),
                fat_g=float(fi.fat_g),
                carb_g=float(fi.carb_g),
                calcium_mg=float(fi.calcium_mg or 0),
                phosphorus_mg=float(fi.phosphorus_mg or 0),
                omega3_mg=float(fi.omega3_mg or 0),
                taurine_mg=float(fi.taurine_mg or 0),
                source="db",
            )
        return await self._deepseek_lookup(product_name)

    def calculate_grams(self, gap_kcal: float, kcal_per_100g: float) -> float:
        raw = gap_kcal * 0.5 / (kcal_per_100g / 100)
        return round(max(20.0, min(200.0, raw)), 0)

    def calculate_progress(self, items: list[dict], target: dict) -> dict:
        totals = self._sum_items(items)
        progress = {}
        for key, tval in target.items():
            if tval and tval > 0:
                progress[f"{key}_pct"] = round(totals.get(key, 0) / tval * 100, 0)
        return progress

    def is_done(self, items: list[dict], target: dict) -> bool:
        totals = self._sum_items(items)
        kcal_pct = totals.get("kcal", 0) / target.get("kcal", 1) * 100
        prot_pct = totals.get("protein_g", 0) / target.get("protein_g", 1) * 100
        return kcal_pct >= 90 and prot_pct >= 90

    def get_recommendation(self, items: list[dict], target: dict,
                           food_items: list[FoodItem], species: str) -> str:
        totals = self._sum_items(items)
        gap_kcal = target.get("kcal", 0) - totals.get("kcal", 0)
        gap_prot = target.get("protein_g", 0) - totals.get("protein_g", 0)
        gap_fat  = target.get("fat_g", 0) - totals.get("fat_g", 0)

        candidates = [f for f in food_items if f.species in (species, "all")]
        if not candidates:
            return ""

        def score(fi: FoodItem) -> float:
            return (
                float(fi.kcal_per_100g) * 0.5
                + float(fi.protein_g) * 2.0 * (1 if gap_prot > 0 else 0)
                + float(fi.fat_g) * 1.0 * (1 if gap_fat > 0 else 0)
            )

        best = max(candidates, key=score)
        parts = []
        if gap_kcal > target.get("kcal", 1) * 0.15:
            parts.append("калорий")
        if gap_prot > target.get("protein_g", 1) * 0.15:
            parts.append("белка")
        if gap_fat > target.get("fat_g", 1) * 0.15:
            parts.append("жиров")

        if parts:
            return f"Не хватает {', '.join(parts)}. Попробуй добавить {best.name}."
        return f"Осталось совсем немного. Можно добавить {best.name}."

    def get_summary_tip(self, totals: dict, target: dict,
                        required_micros: list[str]) -> str:
        tips = []
        ca = totals.get("calcium_mg", 0)
        p  = totals.get("phosphorus_mg", 0)
        if p > 0 and (ca / p) < 1.2:
            tips.append("Ca:P ниже нормы — добавь яичную скорлупу или кунжут")
        for micro in required_micros:
            if micro in ("calcium_mg", "phosphorus_mg"):
                continue
            tval = target.get(micro, 0)
            got  = totals.get(micro, 0)
            if tval > 0 and got < tval * 0.9:
                if micro == "omega3_mg":
                    tips.append("Не хватает Омега-3 — добавь ½ ч.л. льняного или рыбьего масла")
                elif micro == "taurine_mg":
                    tips.append("Не хватает таурина — обязателен для кошек в натуральном рационе")
        return ". ".join(tips) if tips else ""

    # ── Private helpers ─────────────────────────────────────────────

    def _sum_items(self, items: list[dict]) -> dict:
        keys = ["kcal", "protein_g", "fat_g", "carb_g",
                "calcium_mg", "phosphorus_mg", "omega3_mg", "taurine_mg"]
        return {k: round(sum(i.get(k, 0) for i in items), 2) for k in keys}

    async def _deepseek_lookup(self, product_name: str) -> FoodLookupResult | None:
        cached = await self.repo.get_cached_lookup(product_name)
        if cached:
            return self._dict_to_lookup(product_name, cached)

        prompt = (
            f"Дай точные данные КБЖУ и микронутриентов на 100г для продукта: «{product_name}».\n"
            "Ответь ТОЛЬКО в JSON без пояснений:\n"
            '{"kcal":0,"protein_g":0,"fat_g":0,"carb_g":0,'
            '"calcium_mg":0,"phosphorus_mg":0,"omega3_mg":0,"taurine_mg":0,'
            '"category":"meat","confidence":0.9}'
        )
        try:
            response = await self._deepseek.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1,
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
        except Exception as e:
            logger.error(f"DeepSeek lookup failed for '{product_name}': {e}")
            return None

        if not self._validate_range(data.get("category", ""), data.get("kcal", 0)):
            logger.warning(f"Range guard failed for '{product_name}': {data}")
            return None
        if not self._validate_math(data):
            logger.warning(f"Math guard failed for '{product_name}': {data}")
            return None

        await self.repo.cache_lookup(product_name, data)
        return self._dict_to_lookup(product_name, data)

    def _validate_range(self, category: str, kcal: float) -> bool:
        if category not in RANGE_GUARD:
            return True
        lo, hi = RANGE_GUARD[category]
        return lo <= kcal <= hi

    def _validate_math(self, data: dict) -> bool:
        kcal = data.get("kcal", 0)
        if kcal <= 0:
            return False
        calc = (data.get("protein_g", 0) * 4
                + data.get("fat_g", 0) * 9
                + data.get("carb_g", 0) * 4)
        return abs(calc - kcal) / kcal <= 0.15

    def _dict_to_lookup(self, name: str, d: dict) -> FoodLookupResult:
        conf = d.get("confidence", 1.0)
        return FoodLookupResult(
            name=name, grams=0,
            kcal=float(d.get("kcal", 0)),
            protein_g=float(d.get("protein_g", 0)),
            fat_g=float(d.get("fat_g", 0)),
            carb_g=float(d.get("carb_g", 0)),
            calcium_mg=float(d.get("calcium_mg", 0)),
            phosphorus_mg=float(d.get("phosphorus_mg", 0)),
            omega3_mg=float(d.get("omega3_mg", 0)),
            taurine_mg=float(d.get("taurine_mg", 0)),
            source="deepseek_cache",
            confidence=conf,
            low_confidence=conf < 0.7,
        )
