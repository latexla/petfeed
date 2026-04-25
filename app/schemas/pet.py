from datetime import datetime
from pydantic import BaseModel, field_validator

ALLOWED_SPECIES = ["cat", "dog", "rodent", "bird", "reptile"]
ALLOWED_GOALS = ["maintain", "lose", "gain", "growth"]
ALLOWED_ACTIVITY = ["low", "moderate", "high", "working"]
ALLOWED_PHYSIO = ["normal", "pregnant", "lactating", "recovery"]


class PetCreate(BaseModel):
    name: str
    species: str
    breed: str | None = None
    age_months: int
    weight_kg: float
    goal: str = "maintain"
    is_neutered: bool = False
    activity_level: str = "moderate"
    physio_status: str = "normal"
    food_category_id: int | None = None

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

    @field_validator("activity_level")
    @classmethod
    def validate_activity(cls, v):
        if v not in ALLOWED_ACTIVITY:
            raise ValueError(f"invalid_activity. Allowed: {ALLOWED_ACTIVITY}")
        return v

    @field_validator("physio_status")
    @classmethod
    def validate_physio(cls, v):
        if v not in ALLOWED_PHYSIO:
            raise ValueError(f"invalid_physio. Allowed: {ALLOWED_PHYSIO}")
        return v


class PetUpdate(BaseModel):
    name: str | None = None
    breed: str | None = None
    age_months: int | None = None
    weight_kg: float | None = None
    goal: str | None = None
    is_neutered: bool | None = None
    activity_level: str | None = None
    physio_status: str | None = None
    food_category_id: int | None = None


class PetResponse(BaseModel):
    id: int
    name: str
    species: str
    breed: str | None
    age_months: int
    weight_kg: float
    goal: str
    is_neutered: bool
    activity_level: str
    physio_status: str
    food_category_id: int | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
