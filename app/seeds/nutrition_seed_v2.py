"""
Начальные данные для food_categories, breed_risks, stop_foods.
Запуск: python -m app.seeds.nutrition_seed_v2
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import settings
from app.models.food_category import FoodCategory
from app.models.breed_risk import BreedRisk
from app.models.stop_food import StopFood


FOOD_CATEGORIES = [
    {"name": "Сухой корм (стандарт)", "food_type": "dry",
     "kcal_per_100g": 350, "protein_pct": 26, "fat_pct": 14, "fiber_pct": 3},
    {"name": "Влажный корм (стандарт)", "food_type": "wet",
     "kcal_per_100g": 85, "protein_pct": 8, "fat_pct": 5, "fiber_pct": 0.5},
    {"name": "Натуральный (мясо+овощи)", "food_type": "natural",
     "kcal_per_100g": 150, "protein_pct": 18, "fat_pct": 10, "fiber_pct": 2},
    {"name": "BARF (сырое)", "food_type": "raw",
     "kcal_per_100g": 130, "protein_pct": 17, "fat_pct": 9, "fiber_pct": 1},
]

BREED_RISKS = [
    {"breed_name": "Jack Russell Terrier", "risk_key": "atopy"},
    {"breed_name": "Jack Russell Terrier", "risk_key": "patellar_luxation"},
    {"breed_name": "Jack Russell Terrier", "risk_key": "obesity"},
    {"breed_name": "Jack Russell Terrier", "risk_key": "hypoglycemia_puppies"},
    {"breed_name": "Джек Рассел Терьер", "risk_key": "atopy"},
    {"breed_name": "Джек Рассел Терьер", "risk_key": "patellar_luxation"},
    {"breed_name": "Джек Рассел Терьер", "risk_key": "obesity"},
    {"breed_name": "Джек Рассел Терьер", "risk_key": "hypoglycemia_puppies"},
]

STOP_FOODS = [
    # Уровень 1 — Универсальные токсины (Cortinovis & Caloni 2016; ASPCA)
    {"species": "all", "level": 1, "product_name": "Шоколад, какао, кофе",
     "toxic_component": "Метилксантины (теобромин, кофеин)",
     "clinical_effect": "Аритмия, судороги, рвота, гибель",
     "source": "Cortinovis & Caloni 2016"},
    {"species": "all", "level": 1, "product_name": "Лук, чеснок, лук-порей (Allium spp.)",
     "toxic_component": "Органосульфоксиды → сульфиды",
     "clinical_effect": "Окислительный гемолиз, гемолитическая анемия",
     "source": "Cortinovis & Caloni 2016"},
    {"species": "all", "level": 1, "product_name": "Виноград, изюм, коринка",
     "toxic_component": "Виннокаменная кислота (вероятно)",
     "clinical_effect": "Острая почечная недостаточность",
     "source": "ASPCA APCC"},
    {"species": "all", "level": 1, "product_name": "Ксилитол (жвачки, выпечка)",
     "toxic_component": "Ксилитол → гиперинсулинемия",
     "clinical_effect": "Гипогликемия, поражение печени",
     "source": "ASPCA APCC"},
    {"species": "all", "level": 1, "product_name": "Орехи макадамия",
     "toxic_component": "Механизм не установлен",
     "clinical_effect": "Слабость, тремор, гипертермия до 48ч",
     "source": "ASPCA APCC"},
    {"species": "all", "level": 1, "product_name": "Авокадо",
     "toxic_component": "Персин (мякоть, листья, кожура, косточка)",
     "clinical_effect": "Рвота, диарея, угнетение",
     "source": "ASPCA APCC"},
    {"species": "all", "level": 1, "product_name": "Алкоголь",
     "toxic_component": "Этанол",
     "clinical_effect": "Угнетение ЦНС, ацидоз, кома, гибель",
     "source": "Cortinovis & Caloni 2016"},
    {"species": "all", "level": 1, "product_name": "Сырое дрожжевое тесто",
     "toxic_component": "Этанол (ферментация) + расширение",
     "clinical_effect": "Вздутие желудка + алкогольная интоксикация",
     "source": "ASPCA APCC"},
    # Уровень 2 — Нутриционально нежелательные (NRC 2006, Merck)
    {"species": "all", "level": 2, "product_name": "Сырые яйца (белок)",
     "toxic_component": "Авидин разрушает биотин (B7)",
     "clinical_effect": "Дефицит биотина → дерматит, алопеция",
     "source": "NRC 2006"},
    {"species": "all", "level": 2, "product_name": "Сырая рыба (регулярно)",
     "toxic_component": "Тиаминазы разрушают тиамин (B1)",
     "clinical_effect": "Дефицит B1 → неврологические нарушения",
     "source": "NRC 2006"},
    {"species": "all", "level": 2, "product_name": "Сырые соевые бобы",
     "toxic_component": "Ингибиторы трипсина",
     "clinical_effect": "Нарушение переваривания белка",
     "source": "NRC 2006"},
    {"species": "all", "level": 2, "product_name": "Варёные кости",
     "toxic_component": "Расщепляются на острые осколки",
     "clinical_effect": "Перфорация ЖКТ, непроходимость",
     "source": "Merck Veterinary Manual"},
    {"species": "all", "level": 2, "product_name": "Исключительно мясной рацион",
     "toxic_component": "Нарушение соотношения Ca:P",
     "clinical_effect": "Вторичный гиперпаратиреоз, деминерализация",
     "source": "NRC 2006"},
    {"species": "all", "level": 2, "product_name": "Беззерновые диеты (без показаний)",
     "toxic_component": "Связь с DCM (расследование FDA)",
     "clinical_effect": "Дилатационная кардиомиопатия",
     "source": "FDA 2019"},
    # Уровень 3 — Информационный (только для пород с атопией)
    {"species": "dog", "level": 3,
     "product_name": "Говядина, молочные продукты, пшеница, курица",
     "toxic_component": "Пищевые аллергены (индивидуально)",
     "clinical_effect": "Атопический дерматит — триггер у предрасположенных пород",
     "source": "Cornell Vet; Wilhelm et al. 2011"},
]


async def seed():
    engine = create_async_engine(settings.async_database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        for data in FOOD_CATEGORIES:
            session.add(FoodCategory(**data))
        for data in BREED_RISKS:
            session.add(BreedRisk(**data))
        for data in STOP_FOODS:
            session.add(StopFood(**data))
        await session.commit()
    await engine.dispose()
    print("Seed v2 complete")


if __name__ == "__main__":
    asyncio.run(seed())
