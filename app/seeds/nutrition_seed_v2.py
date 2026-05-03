"""
Начальные данные для food_categories, breed_risks, stop_foods.
Запуск: python -m app.seeds.nutrition_seed_v2
"""
import asyncio
import ssl
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
    # --- DOGS ---
    {"breed_name": "Jack Russell Terrier", "risk_key": "atopy"},
    {"breed_name": "Jack Russell Terrier", "risk_key": "patellar_luxation"},
    {"breed_name": "Jack Russell Terrier", "risk_key": "obesity"},
    {"breed_name": "Jack Russell Terrier", "risk_key": "hypoglycemia_puppies"},
    {"breed_name": "Джек Рассел Терьер", "risk_key": "atopy"},
    {"breed_name": "Джек Рассел Терьер", "risk_key": "patellar_luxation"},
    {"breed_name": "Джек Рассел Терьер", "risk_key": "obesity"},
    {"breed_name": "Джек Рассел Терьер", "risk_key": "hypoglycemia_puppies"},

    # --- CATS ---
    # risk_key vocabulary for cats:
    #   obesity           → снижать MER-коэффициент (обрабатывается в _base_coefficient)
    #   hcm               → предупреждать о таурине и Омега-3, рекомендовать ЭхоКГ
    #   pkd               → предупреждать о генетическом тесте PKD, ограничение P при ХБП
    #   high_caloric_need → сфинкс: MER выше стандарта (нет шерсти → теплопотери)
    #   taurine_risk      → при натуральном рационе — добавка таурина обязательна
    #   renal_amyloidosis → абиссинская: риск почечного амилоидоза → биохимия с 5 лет
    #   liver_amyloidosis → сиамская/ориентальная: риск гепатического амилоидоза
    #   hypokalemia       → бурманская/девон-рекс/тонкинская: контроль K⁺
    #   diabetes_risk     → бурманская: повышенный риск СД → контроль BCS, углеводы
    #   ocd_joints        → шотландская вислоухая: остеохондродисплазия → Омега-3, вес
    #   flutd_risk        → русская голубая: стресс-FLUTD → влажный корм, магний
    #   pra               → бенгальская/абиссинская: таурин + DHA обязательны
    #   ibd               → бенгальская: воспалительная болезнь кишечника
    #   slow_maturation   → мейн-кун/рэгдолл/норвежская: рацион роста до 18 мес

    # Persian / Персидская
    {"breed_name": "Persian",     "risk_key": "obesity"},
    {"breed_name": "Persian",     "risk_key": "pkd"},
    {"breed_name": "Персидская",  "risk_key": "obesity"},
    {"breed_name": "Персидская",  "risk_key": "pkd"},

    # Maine Coon / Мейн-кун
    {"breed_name": "Maine Coon",  "risk_key": "hcm"},
    {"breed_name": "Maine Coon",  "risk_key": "taurine_risk"},
    {"breed_name": "Maine Coon",  "risk_key": "slow_maturation"},
    {"breed_name": "Мейн-кун",    "risk_key": "hcm"},
    {"breed_name": "Мейн-кун",    "risk_key": "taurine_risk"},
    {"breed_name": "Мейн-кун",    "risk_key": "slow_maturation"},

    # Ragdoll / Рэгдолл
    {"breed_name": "Ragdoll",     "risk_key": "hcm"},
    {"breed_name": "Ragdoll",     "risk_key": "obesity"},
    {"breed_name": "Ragdoll",     "risk_key": "slow_maturation"},
    {"breed_name": "Рэгдолл",     "risk_key": "hcm"},
    {"breed_name": "Рэгдолл",     "risk_key": "obesity"},
    {"breed_name": "Рэгдолл",     "risk_key": "slow_maturation"},

    # British Shorthair / Британская
    {"breed_name": "British Shorthair",         "risk_key": "obesity"},
    {"breed_name": "British Shorthair",         "risk_key": "hcm"},
    {"breed_name": "Британская короткошёрстная","risk_key": "obesity"},
    {"breed_name": "Британская короткошёрстная","risk_key": "hcm"},

    # Siamese / Сиамская
    {"breed_name": "Siamese",   "risk_key": "liver_amyloidosis"},
    {"breed_name": "Сиамская",  "risk_key": "liver_amyloidosis"},

    # Scottish Fold / Шотландская вислоухая
    {"breed_name": "Scottish Fold",          "risk_key": "ocd_joints"},
    {"breed_name": "Scottish Fold",          "risk_key": "obesity"},
    {"breed_name": "Шотландская вислоухая",  "risk_key": "ocd_joints"},
    {"breed_name": "Шотландская вислоухая",  "risk_key": "obesity"},

    # Sphynx / Сфинкс
    {"breed_name": "Sphynx",   "risk_key": "hcm"},
    {"breed_name": "Sphynx",   "risk_key": "high_caloric_need"},
    {"breed_name": "Sphynx",   "risk_key": "taurine_risk"},
    {"breed_name": "Сфинкс",   "risk_key": "hcm"},
    {"breed_name": "Сфинкс",   "risk_key": "high_caloric_need"},
    {"breed_name": "Сфинкс",   "risk_key": "taurine_risk"},

    # Bengal / Бенгальская
    {"breed_name": "Bengal",       "risk_key": "pra"},
    {"breed_name": "Bengal",       "risk_key": "ibd"},
    {"breed_name": "Бенгальская",  "risk_key": "pra"},
    {"breed_name": "Бенгальская",  "risk_key": "ibd"},

    # Russian Blue / Русская голубая
    {"breed_name": "Russian Blue",      "risk_key": "obesity"},
    {"breed_name": "Russian Blue",      "risk_key": "flutd_risk"},
    {"breed_name": "Русская голубая",   "risk_key": "obesity"},
    {"breed_name": "Русская голубая",   "risk_key": "flutd_risk"},

    # Norwegian Forest Cat / Норвежская лесная
    {"breed_name": "Norwegian Forest Cat",  "risk_key": "obesity"},
    {"breed_name": "Norwegian Forest Cat",  "risk_key": "hcm"},
    {"breed_name": "Norwegian Forest Cat",  "risk_key": "slow_maturation"},
    {"breed_name": "Норвежская лесная",     "risk_key": "obesity"},
    {"breed_name": "Норвежская лесная",     "risk_key": "hcm"},
    {"breed_name": "Норвежская лесная",     "risk_key": "slow_maturation"},

    # Abyssinian / Абиссинская
    {"breed_name": "Abyssinian",    "risk_key": "renal_amyloidosis"},
    {"breed_name": "Abyssinian",    "risk_key": "pra"},
    {"breed_name": "Абиссинская",   "risk_key": "renal_amyloidosis"},
    {"breed_name": "Абиссинская",   "risk_key": "pra"},

    # Devon Rex / Девон-рекс
    {"breed_name": "Devon Rex",     "risk_key": "hypokalemia"},
    {"breed_name": "Девон-рекс",    "risk_key": "hypokalemia"},

    # Birman / Бирманская
    {"breed_name": "Birman",       "risk_key": "obesity"},
    {"breed_name": "Бирманская",   "risk_key": "obesity"},

    # Burmese / Бурманская
    {"breed_name": "Burmese",      "risk_key": "hypokalemia"},
    {"breed_name": "Burmese",      "risk_key": "diabetes_risk"},
    {"breed_name": "Burmese",      "risk_key": "obesity"},
    {"breed_name": "Бурманская",   "risk_key": "hypokalemia"},
    {"breed_name": "Бурманская",   "risk_key": "diabetes_risk"},
    {"breed_name": "Бурманская",   "risk_key": "obesity"},

    # Turkish Angora / Турецкая ангора
    {"breed_name": "Turkish Angora",    "risk_key": "hcm"},
    {"breed_name": "Турецкая ангора",   "risk_key": "hcm"},

    # Oriental Shorthair / Ориентальная
    {"breed_name": "Oriental Shorthair",    "risk_key": "liver_amyloidosis"},
    {"breed_name": "Ориентальная",          "risk_key": "liver_amyloidosis"},

    # Exotic Shorthair / Экзотическая
    {"breed_name": "Exotic Shorthair",              "risk_key": "obesity"},
    {"breed_name": "Exotic Shorthair",              "risk_key": "pkd"},
    {"breed_name": "Экзотическая короткошёрстная",  "risk_key": "obesity"},
    {"breed_name": "Экзотическая короткошёрстная",  "risk_key": "pkd"},

    # American Shorthair / Американская
    {"breed_name": "American Shorthair",              "risk_key": "hcm"},
    {"breed_name": "American Shorthair",              "risk_key": "obesity"},
    {"breed_name": "Американская короткошёрстная",    "risk_key": "hcm"},
    {"breed_name": "Американская короткошёрстная",    "risk_key": "obesity"},

    # Siberian / Сибирская
    {"breed_name": "Siberian",    "risk_key": "hcm"},
    {"breed_name": "Siberian",    "risk_key": "obesity"},
    {"breed_name": "Siberian",    "risk_key": "slow_maturation"},
    {"breed_name": "Сибирская",   "risk_key": "hcm"},
    {"breed_name": "Сибирская",   "risk_key": "obesity"},
    {"breed_name": "Сибирская",   "risk_key": "slow_maturation"},

    # Tonkinese / Тонкинская
    {"breed_name": "Tonkinese",   "risk_key": "hcm"},
    {"breed_name": "Tonkinese",   "risk_key": "hypokalemia"},
    {"breed_name": "Тонкинская",  "risk_key": "hcm"},
    {"breed_name": "Тонкинская",  "risk_key": "hypokalemia"},
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
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    engine = create_async_engine(settings.async_database_url, connect_args={"ssl": ssl_ctx})
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
