from datetime import datetime
from pydantic import BaseModel, field_validator

ALLOWED_SPECIES = ["cat", "dog", "rodent", "bird", "reptile"]
ALLOWED_GOALS = ["maintain", "lose", "gain", "growth"]


class PetCreate(BaseModel):
    name: str
    species: str
    breed: str | None = None
    age_months: int
    weight_kg: float
    goal: str = "maintain"

    @field_validator("species")
    @classmethod
    def validate_species(cls, v):
        if v not in ALLOWED_SPECIES:
            raise ValueError(f"invalid_species. Allowed: {ALLOWED_SPECIES}")
        return v

    @field_validator("weight_kg")
    @classmethod
    def validate_weight(cls, v):
        if v <= 0:
            raise ValueError("weight_kg must be > 0")
        return v


class PetUpdate(BaseModel):
    name: str | None = None
    breed: str | None = None
    age_months: int | None = None
    weight_kg: float | None = None
    goal: str | None = None


class PetResponse(BaseModel):
    id: int
    name: str
    species: str
    breed: str | None
    age_months: int
    weight_kg: float
    goal: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
