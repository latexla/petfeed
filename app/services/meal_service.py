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

# Maximum tolerable levels per 1000 kcal (NRC 2006 / AAFCO 2024)
# Source: NRC "Nutrient Requirements of Dogs and Cats" 2006; AAFCO Official Publication 2024
MICRO_MAX_PER_1000KCAL: dict[str, dict[str, float]] = {
    "dog": {
        "calcium_mg":    4500,   # NRC MTL; large-breed puppies: 2500 (checked separately)
        "phosphorus_mg": 4000,   # NRC MTL; Ca:P must stay ≤ 2:1
        "calcium_mg_puppy_large": 2500,  # NRC MTL for growing dogs >25 kg adult weight
    },
    "cat": {
        "calcium_mg":    4500,   # NRC MTL adult cats
        "phosphorus_mg": 4400,   # NRC MTL; restrict to <1000 in CKD
        "magnesium_mg":  100,    # AAFCO max per 1000 kcal (~0.10 % DM); struvite risk
    },
}

# Maximum daily calorie excess vs calculated MER (fraction above 1.0)
# Beyond this → obesity / pancreatitis risk
MER_MAX_OVERAGE: float = 0.20  # +20 %

# Macronutrient share of meal kcal thresholds (% of total meal energy)
# Source: Lem et al. JAVMA 2008 (fat/pancreatitis); Godfrey et al. J Anim Sci 2025 (carbs/cats);
#         NRC 2006 (no MTL for macros in healthy animals)
# Protein note: direct evidence of kidney damage in HEALTHY dogs from high protein is weak but
# the hyperfiltration mechanism is real; pig studies show fibrosis at 35% ME (PMID:20668252).
# Thresholds here are for extreme imbalance flags, not toxicity cutoffs.
MACRO_PCT_WARN: dict[str, dict[str, float]] = {
    "dog": {"fat": 40.0, "protein": 55.0, "carb": 65.0},
    "cat": {"fat": 50.0, "protein": 70.0, "carb": 45.0},
}
MACRO_PCT_STOP: dict[str, dict[str, float]] = {
    "dog": {"fat": 55.0},
    "cat": {"fat": 65.0},
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

    def get_excess_warnings(
        self,
        totals: dict,
        target_kcal: float,
        species: str,
        age_months: int,
        weight_kg: float,
    ) -> list[str]:
        """Return warning strings when meal totals exceed safe upper limits.

        Limits source: NRC 2006, AAFCO 2024.
        totals      — суммарные нутриенты одного приёма пищи (ккал + мг).
        target_kcal — целевая калорийность этого приёма пищи (daily_calories / meals_per_day).
        """
        warnings: list[str] = []
        meal_kcal = totals.get("kcal", 0)
        if meal_kcal <= 0:
            return warnings

        # Scale meal totals to per-1000-kcal for NRC/AAFCO limit comparison
        factor = 1000 / meal_kcal

        ca_per_1000 = totals.get("calcium_mg", 0) * factor
        p_per_1000  = totals.get("phosphorus_mg", 0) * factor
        mg_per_1000 = totals.get("magnesium_mg", 0) * factor

        maxes = MICRO_MAX_PER_1000KCAL.get(species, {})

        # ── Calcium ────────────────────────────────────────────────────────
        ca_limit = maxes.get("calcium_mg", 0)
        is_large_breed_puppy = age_months < 12 and weight_kg > 15
        if is_large_breed_puppy:
            ca_limit = maxes.get("calcium_mg_puppy_large", ca_limit)

        if ca_limit and ca_per_1000 > ca_limit:
            tip = (
                f"⚠️ Кальций превышен: {ca_per_1000:.0f} мг/1000 ккал "
                f"(макс. {ca_limit:.0f} мг/1000 ккал, NRC 2006)"
            )
            if is_large_breed_puppy:
                tip += " — особенно опасно для щенков крупных пород (риск остеохондроза)"
            warnings.append(tip)

        # ── Phosphorus ─────────────────────────────────────────────────────
        p_limit = maxes.get("phosphorus_mg", 0)
        if p_limit and p_per_1000 > p_limit:
            warnings.append(
                f"⚠️ Фосфор превышен: {p_per_1000:.0f} мг/1000 ккал "
                f"(макс. {p_limit:.0f} мг/1000 ккал, NRC 2006)"
            )

        # ── Ca:P ratio ─────────────────────────────────────────────────────
        ca_abs = totals.get("calcium_mg", 0)
        p_abs  = totals.get("phosphorus_mg", 0)
        if p_abs > 0 and ca_abs / p_abs > 2.0:
            warnings.append(
                f"⚠️ Ca:P = {ca_abs/p_abs:.1f}:1 — превышает максимум 2:1 "
                "(AAFCO); снизь кальциевые добавки"
            )

        # ── Magnesium (cats only — struvite risk) ──────────────────────────
        if species == "cat":
            mg_limit = maxes.get("magnesium_mg", 0)
            if mg_limit and mg_per_1000 > mg_limit:
                warnings.append(
                    f"⚠️ Магний превышен: {mg_per_1000:.0f} мг/1000 ккал "
                    f"(макс. {mg_limit:.0f} мг/1000 ккал, AAFCO) — риск струвитных уролитов"
                )

        # ── Calorie excess vs per-meal target ──────────────────────────────
        if target_kcal > 0 and meal_kcal > target_kcal * (1 + MER_MAX_OVERAGE):
            pct = round((meal_kcal / target_kcal - 1) * 100)
            warnings.append(
                f"⚠️ Калорийность приёма пищи превышает норму на {pct}% "
                f"({meal_kcal:.0f} vs {target_kcal:.0f} ккал) — риск ожирения"
            )

        # ── Macronutrient balance (% of meal kcal) ─────────────────────────
        fat_kcal  = totals.get("fat_g", 0) * 9
        prot_kcal = totals.get("protein_g", 0) * 4
        carb_kcal = totals.get("carb_g", 0) * 4

        warn_pct = MACRO_PCT_WARN.get(species, {})
        stop_pct = MACRO_PCT_STOP.get(species, {})

        fat_pct  = fat_kcal  / meal_kcal * 100
        prot_pct = prot_kcal / meal_kcal * 100
        carb_pct = carb_kcal / meal_kcal * 100

        fat_stop = stop_pct.get("fat", 0)
        fat_warn = warn_pct.get("fat", 0)
        if fat_stop and fat_pct > fat_stop:
            warnings.append(
                f"🔴 Жир: {fat_pct:.0f}% калорийности — критически высокий уровень "
                f"(макс. {fat_stop:.0f}%, Lem et al. 2008) — острый риск панкреатита"
            )
        elif fat_warn and fat_pct > fat_warn:
            warnings.append(
                f"⚠️ Жир: {fat_pct:.0f}% калорийности (рек. макс. {fat_warn:.0f}%) — "
                "повышенный риск гипертриглицеридемии и панкреатита"
            )

        prot_warn = warn_pct.get("protein", 0)
        if prot_warn and prot_pct > prot_warn:
            warnings.append(
                f"⚠️ Белок: {prot_pct:.0f}% калорийности (рек. макс. {prot_warn:.0f}%) — "
                "крайний дисбаланс рациона; обеспечь достаточное потребление воды; "
                "при заболеваниях почек — обязательно снизить и проконсультироваться с ветеринаром"
            )

        carb_warn = warn_pct.get("carb", 0)
        if carb_warn and carb_pct > carb_warn:
            if species == "cat":
                warnings.append(
                    f"⚠️ Углеводы: {carb_pct:.0f}% калорийности (рек. макс. {carb_warn:.0f}% для кошек) — "
                    "кошки — облигатные хищники; постпрандиальная гипергликемия при ≥43% ME (Verbrugghe 2017)"
                )
            else:
                warnings.append(
                    f"⚠️ Углеводы: {carb_pct:.0f}% калорийности (рек. макс. {carb_warn:.0f}%) — "
                    "несбалансированный рацион, риск ожирения"
                )

        return warnings

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
