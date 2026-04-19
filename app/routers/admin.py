from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.config import settings
from app.models.user import User
from app.models.pet import Pet
from app.models.feature_flag import FeatureFlag
from app.models.nutrition_knowledge import NutritionKnowledge

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")

COOKIE_NAME = "admin_token"


def check_auth(request: Request) -> bool:
    return request.cookies.get(COOKIE_NAME) == settings.ADMIN_TOKEN


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    html = f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>Admin Login</title>
    <style>body{{font-family:system-ui;display:flex;justify-content:center;align-items:center;height:100vh;background:#f5f5f5}}
    .box{{background:white;padding:32px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);width:320px}}
    h2{{margin-bottom:20px}}input{{width:100%;padding:8px;border:1px solid #ddd;border-radius:4px;margin-bottom:12px;font-size:14px}}
    button{{width:100%;padding:10px;background:#4f46e5;color:white;border:none;border-radius:4px;cursor:pointer}}
    .err{{color:red;font-size:13px;margin-bottom:8px}}</style></head>
    <body><div class="box"><h2>🐾 PetFeed Admin</h2>
    {"<p class='err'>Неверный токен</p>" if error else ""}
    <form method="post" action="/admin/login">
    <input type="password" name="token" placeholder="Admin token" autofocus>
    <button type="submit">Войти</button></form></div></body></html>
    """
    return HTMLResponse(html)


@router.post("/login")
async def login(request: Request):
    form = await request.form()
    token = form.get("token", "")
    if token == settings.ADMIN_TOKEN:
        response = RedirectResponse("/admin/", status_code=302)
        response.set_cookie(COOKIE_NAME, token, httponly=True, max_age=86400 * 7)
        return response
    return RedirectResponse("/admin/login?error=1", status_code=302)


@router.get("/logout")
async def logout():
    response = RedirectResponse("/admin/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: AsyncSession = Depends(get_db)):
    if not check_auth(request):
        return RedirectResponse("/admin/login")
    users_count = (await db.execute(select(func.count(User.id)))).scalar()
    pets_count = (await db.execute(select(func.count(Pet.id)))).scalar()
    nutrition_count = (await db.execute(select(func.count(NutritionKnowledge.id)))).scalar()
    return templates.TemplateResponse(request, "admin/index.html", {
        "stats": {"users": users_count, "pets": pets_count, "nutrition": nutrition_count}
    })


@router.get("/users", response_class=HTMLResponse)
async def users_list(request: Request, db: AsyncSession = Depends(get_db)):
    if not check_auth(request):
        return RedirectResponse("/admin/login")
    users = (await db.execute(select(User).order_by(User.created_at.desc()))).scalars().all()
    return templates.TemplateResponse(request, "admin/users.html", {"users": users})


@router.get("/flags", response_class=HTMLResponse)
async def flags_list(request: Request, db: AsyncSession = Depends(get_db)):
    if not check_auth(request):
        return RedirectResponse("/admin/login")
    flags = (await db.execute(select(FeatureFlag).order_by(FeatureFlag.key))).scalars().all()
    return templates.TemplateResponse(request, "admin/flags.html", {"flags": flags})


@router.post("/flags/{flag_id}/toggle")
async def toggle_flag(flag_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    if not check_auth(request):
        return RedirectResponse("/admin/login")
    flag = (await db.execute(select(FeatureFlag).where(FeatureFlag.id == flag_id))).scalar_one_or_none()
    if flag:
        flag.is_enabled = not flag.is_enabled
        await db.commit()
    return RedirectResponse("/admin/flags", status_code=302)


@router.get("/nutrition", response_class=HTMLResponse)
async def nutrition_list(request: Request, db: AsyncSession = Depends(get_db)):
    if not check_auth(request):
        return RedirectResponse("/admin/login")
    records = (await db.execute(select(NutritionKnowledge).order_by(NutritionKnowledge.species, NutritionKnowledge.goal))).scalars().all()
    return templates.TemplateResponse(request, "admin/nutrition.html", {"records": records})


@router.post("/nutrition/seed")
async def seed_nutrition(request: Request, db: AsyncSession = Depends(get_db)):
    if not check_auth(request):
        return RedirectResponse("/admin/login")
    existing = (await db.execute(select(NutritionKnowledge))).scalars().first()
    if not existing:
        records = [
            NutritionKnowledge(species="cat", goal="maintain", rer_multiplier=1.2, meals_per_day=2, kcal_per_100g=350.0, stop_foods="лук, чеснок, виноград, шоколад", notes="Облигатный хищник"),
            NutritionKnowledge(species="cat", goal="lose", rer_multiplier=0.8, meals_per_day=3, kcal_per_100g=300.0, stop_foods="лук, чеснок, виноград, шоколад", notes="Снижение веса"),
            NutritionKnowledge(species="cat", goal="gain", rer_multiplier=1.4, meals_per_day=3, kcal_per_100g=400.0, stop_foods="лук, чеснок, виноград, шоколад", notes="Набор веса"),
            NutritionKnowledge(species="cat", goal="growth", rer_multiplier=1.6, meals_per_day=4, kcal_per_100g=380.0, stop_foods="лук, чеснок, виноград, шоколад", notes="Котёнок до 1 года"),
            NutritionKnowledge(species="dog", goal="maintain", rer_multiplier=1.3, meals_per_day=2, kcal_per_100g=320.0, stop_foods="лук, виноград, изюм, шоколад, ксилит", notes="Взрослая собака"),
            NutritionKnowledge(species="dog", goal="lose", rer_multiplier=1.0, meals_per_day=3, kcal_per_100g=280.0, stop_foods="лук, виноград, изюм, шоколад, ксилит", notes="Снижение веса"),
            NutritionKnowledge(species="dog", goal="gain", rer_multiplier=1.6, meals_per_day=3, kcal_per_100g=380.0, stop_foods="лук, виноград, изюм, шоколад, ксилит", notes="Набор веса"),
            NutritionKnowledge(species="dog", goal="growth", rer_multiplier=2.0, meals_per_day=4, kcal_per_100g=360.0, stop_foods="лук, виноград, изюм, шоколад, ксилит", notes="Щенок до 1 года"),
            NutritionKnowledge(species="rodent", goal="maintain", rer_multiplier=1.1, meals_per_day=2, kcal_per_100g=250.0, stop_foods="цитрусовые, сахар, соль", notes="Хомяк/крыса/морская свинка"),
            NutritionKnowledge(species="rodent", goal="growth", rer_multiplier=1.4, meals_per_day=3, kcal_per_100g=280.0, stop_foods="цитрусовые, сахар, соль", notes="Молодой грызун"),
            NutritionKnowledge(species="bird", goal="maintain", rer_multiplier=1.0, meals_per_day=2, kcal_per_100g=200.0, stop_foods="авокадо, шоколад, кофеин, соль", notes="Попугай/канарейка"),
            NutritionKnowledge(species="bird", goal="growth", rer_multiplier=1.3, meals_per_day=3, kcal_per_100g=220.0, stop_foods="авокадо, шоколад, кофеин, соль", notes="Птенец"),
            NutritionKnowledge(species="reptile", goal="maintain", rer_multiplier=0.6, meals_per_day=1, kcal_per_100g=180.0, stop_foods="обработанные продукты", notes="Черепаха/ящерица"),
            NutritionKnowledge(species="reptile", goal="growth", rer_multiplier=0.9, meals_per_day=2, kcal_per_100g=200.0, stop_foods="обработанные продукты", notes="Молодая рептилия"),
        ]
        db.add_all(records)
        await db.commit()
    return RedirectResponse("/admin/nutrition?msg=Заполнено+успешно", status_code=302)
