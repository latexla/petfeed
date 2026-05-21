from pydantic import BaseModel
from typing import Literal


class RecommendRequest(BaseModel):
    pet_id: int
    mode: Literal["natural", "commercial"]
    ingredients: list[str] = []   # для natural: ["курица", "гречка"]
    product_name: str = ""        # для commercial: "Royal Canin Adult"


class RecommendItem(BaseModel):
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
    food_item_id: int | None = None


class NutrientMap(BaseModel):
    kcal: float = 0
    protein_g: float = 0
    fat_g: float = 0
    carb_g: float = 0
    calcium_mg: float = 0
    phosphorus_mg: float = 0
    omega3_mg: float = 0
    taurine_mg: float = 0


class RecommendResponse(BaseModel):
    items: list[RecommendItem]
    totals: NutrientMap
    targets: NutrientMap
    micro_coverage: dict[str, float]   # {"calcium_mg": 89.0, ...}
    covers_pct: float
    deficiencies: list[str]
    warnings: list[str]


class DailyAddNamedRequest(BaseModel):
    pet_id: int
    name: str
    grams: float
    kcal_per_100g: float
    protein_g: float
    fat_g: float
    carb_g: float
    calcium_mg: float = 0.0
    phosphorus_mg: float = 0.0
    omega3_mg: float = 0.0
    taurine_mg: float = 0.0
