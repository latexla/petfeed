from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.pet_repo import PetRepository
from app.repositories.nutrition_repo import NutritionRepository
from app.repositories.meal_repo import MealRepository
from app.services.user_service import UserService
from app.services.pet_service import PetService
from app.services.meal_service import MealService

router = APIRouter(prefix="/meal", tags=["meal"])


class AddProductRequest(BaseModel):
    pet_id: int
    product_name: str
    food_type: str  # natural | prepared | mixed
    force_add: bool = False  # bypass Level 2 stop-list warning


@router.post("/add-product")
async def add_product(body: AddProductRequest, request: Request,
                      db: AsyncSession = Depends(get_db)):
    telegram_id = request.state.telegram_id
    user = await UserService(UserRepository(db)).get_or_create(telegram_id=telegram_id)
    pet = await PetService(PetRepository(db)).get_by_id(
        pet_id=body.pet_id, owner_id=user.id
    )
    if pet is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    ration = await NutritionRepository(db).get_ration_by_pet(body.pet_id)
    if ration is None:
        raise HTTPException(status_code=400, detail={"error": "no_ration"})

    svc = MealService(MealRepository(db))
    breed_risks = await NutritionRepository(db).get_breed_risks(pet.breed or "")
    required_micros = svc.get_required_micros(pet.species, breed_risks)

    repo = MealRepository(db)
    session = await repo.get_session(telegram_id, body.pet_id)
    if session is None:
        micro_targets = svc.compute_micro_targets(
            mer=float(ration.daily_calories),
            meals_per_day=ration.meals_per_day,
            species=pet.species,
            required_micros=required_micros,
        )
        target_kcal = round(float(ration.daily_calories) / ration.meals_per_day, 1)
        daily_grams_est = float(ration.daily_calories) / 350 * 100
        pct_prot = 0.225 if pet.age_months < 12 else 0.18
        # Fat target: ~25% of meal kcal for young, ~20% for adults (÷9 kcal/g).
        # AAFCO minimum (5.5% DM) is too low — all real food far exceeds it,
        # making progress look like a permanent 300%+ overshoot.
        fat_pct_kcal = 0.25 if pet.age_months < 12 else 0.20
        session = {
            "food_type": body.food_type,
            "items": [],
            "target": {
                "kcal": target_kcal,
                "protein_g": round(daily_grams_est * pct_prot / ration.meals_per_day, 1),
                "fat_g": round(target_kcal * fat_pct_kcal / 9, 1),
                **micro_targets,
            },
        }

    # 1. Check stop-list (unless force_add for Level 2)
    if not body.force_add:
        stop_foods = await repo.get_stop_foods_for_species(pet.species)
        stop_result = svc.check_stop_list(body.product_name, stop_foods)
        if stop_result.level == 1:
            return {
                "status": "blocked",
                "message": (
                    f"⛔ {stop_result.product_name} нельзя давать этому виду животных! "
                    f"Токсичный компонент: {stop_result.toxic_component}. "
                    f"Эффект: {stop_result.clinical_effect}."
                ),
            }
        if stop_result.level == 2:
            return {
                "status": "warning",
                "message": (
                    f"⚠️ {stop_result.product_name} нежелательно давать регулярно. "
                    f"{stop_result.clinical_effect or ''}. Добавить всё равно?"
                ),
                "product_name": body.product_name,
            }

    # 2. Look up КБЖУ
    lookup = await svc.lookup_product(body.product_name)
    if lookup is None:
        return {
            "status": "not_found",
            "message": f"Не удалось найти данные для «{body.product_name}». Попробуй другое название.",
        }

    grams = svc.calculate_grams(
        gap_kcal=session["target"]["kcal"] - sum(i["kcal"] for i in session["items"]),
        kcal_per_100g=lookup.kcal,
    )
    factor = grams / 100

    item = {
        "name": lookup.name,
        "grams": grams,
        "kcal": round(lookup.kcal * factor, 1),
        "protein_g": round(lookup.protein_g * factor, 1),
        "fat_g": round(lookup.fat_g * factor, 1),
        "carb_g": round(lookup.carb_g * factor, 1),
        "calcium_mg": round(lookup.calcium_mg * factor, 1),
        "phosphorus_mg": round(lookup.phosphorus_mg * factor, 1),
        "omega3_mg": round(lookup.omega3_mg * factor, 1),
        "taurine_mg": round(lookup.taurine_mg * factor, 1),
    }
    session["items"].append(item)
    await repo.save_session(telegram_id, body.pet_id, session)

    progress = svc.calculate_progress(session["items"], session["target"])
    done = svc.is_done(session["items"], session["target"])

    recommendation = ""
    if not done:
        food_items = await repo.get_all_food_items()
        recommendation = svc.get_recommendation(
            session["items"], session["target"], food_items, pet.species
        )

    return {
        "status": "added",
        "item": item,
        "progress": progress,
        "done": done,
        "recommendation": recommendation,
        "low_confidence": lookup.low_confidence,
        "source": lookup.source,
    }


@router.get("/summary/{pet_id}")
async def get_summary(pet_id: int, request: Request,
                      db: AsyncSession = Depends(get_db)):
    telegram_id = request.state.telegram_id
    user = await UserService(UserRepository(db)).get_or_create(telegram_id=telegram_id)
    pet = await PetService(PetRepository(db)).get_by_id(pet_id=pet_id, owner_id=user.id)
    if pet is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    repo = MealRepository(db)
    session = await repo.get_session(telegram_id, pet_id)
    if not session:
        raise HTTPException(status_code=404, detail={"error": "no_session"})

    svc = MealService(repo)
    breed_risks = await NutritionRepository(db).get_breed_risks(pet.breed or "")
    required_micros = svc.get_required_micros(pet.species, breed_risks)

    totals = svc._sum_items(session["items"])
    target = session["target"]

    ca = totals.get("calcium_mg", 0)
    p  = totals.get("phosphorus_mg", 0)
    ca_p_ratio = round(ca / p, 2) if p > 0 else None

    gaps = {
        k: round(totals.get(k, 0) - v, 1)
        for k, v in target.items()
        if totals.get(k, 0) < v * 0.9
    }
    tip = svc.get_summary_tip(totals, target, required_micros)
    excess_warnings = svc.get_excess_warnings(
        totals=totals,
        target_kcal=target.get("kcal", 0),
        species=pet.species,
        age_months=pet.age_months,
        weight_kg=float(pet.weight_kg),
    )

    return {
        "items": session["items"],
        "totals": totals,
        "targets": target,
        "ca_p_ratio": ca_p_ratio,
        "gaps": gaps,
        "tip": tip,
        "excess_warnings": excess_warnings,
        "required_micros": required_micros,
    }


@router.get("/session-check/{pet_id}")
async def check_session(pet_id: int, request: Request,
                        db: AsyncSession = Depends(get_db)):
    telegram_id = request.state.telegram_id
    session = await MealRepository(db).get_session(telegram_id, pet_id)
    items_count = len(session.get("items", [])) if session else 0
    return {"has_session": session is not None, "items_count": items_count}


@router.delete("/reset/{pet_id}")
async def reset_session(pet_id: int, request: Request,
                        db: AsyncSession = Depends(get_db)):
    telegram_id = request.state.telegram_id
    await MealRepository(db).delete_session(telegram_id, pet_id)
    return {"status": "ok"}


@router.post("/undo-last/{pet_id}")
async def undo_last(pet_id: int, request: Request,
                    db: AsyncSession = Depends(get_db)):
    telegram_id = request.state.telegram_id
    updated = await MealRepository(db).undo_last_item(telegram_id, pet_id)
    if updated is None:
        raise HTTPException(status_code=404, detail={"error": "empty_session"})
    return {"status": "ok", "items_count": len(updated.get("items", []))}
