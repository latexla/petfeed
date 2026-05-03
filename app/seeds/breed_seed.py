"""
Seed breeds for dogs and cats.
Run: python3.12 -m app.seeds.breed_seed
"""
import asyncio
import ssl
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import settings
from app.models.breed_registry import BreedRegistry

BREEDS = [
    # --- DOGS ---
    {"canonical_name": "Jack Russell Terrier", "canonical_name_ru": "Джек Рассел Терьер",
     "species": "dog", "aliases": ["JRT", "джек расел", "jack russel", "джек рассел"]},
    {"canonical_name": "Labrador Retriever", "canonical_name_ru": "Лабрадор Ретривер",
     "species": "dog", "aliases": ["лабрадор", "labrador", "лабр"]},
    {"canonical_name": "German Shepherd", "canonical_name_ru": "Немецкая овчарка",
     "species": "dog", "aliases": ["немецкая", "овчарка", "немец", "немецкая овчарка"]},
    {"canonical_name": "French Bulldog", "canonical_name_ru": "Французский бульдог",
     "species": "dog", "aliases": ["француз", "французский", "бульдог", "фрэнч"]},
    {"canonical_name": "Siberian Husky", "canonical_name_ru": "Сибирский хаски",
     "species": "dog", "aliases": ["хаски", "хасик", "husky"]},
    {"canonical_name": "Golden Retriever", "canonical_name_ru": "Золотистый ретривер",
     "species": "dog", "aliases": ["голден", "золотистый", "ретривер"]},
    {"canonical_name": "Yorkshire Terrier", "canonical_name_ru": "Йоркширский терьер",
     "species": "dog", "aliases": ["йорк", "йорки", "йоркширский"]},
    {"canonical_name": "Chihuahua", "canonical_name_ru": "Чихуахуа",
     "species": "dog", "aliases": ["чиха", "чихуа", "чихуахуа"]},
    {"canonical_name": "Pug", "canonical_name_ru": "Мопс",
     "species": "dog", "aliases": ["мопсик"]},
    {"canonical_name": "Pomeranian", "canonical_name_ru": "Шпиц",
     "species": "dog", "aliases": ["шпиц", "помераниан"]},
    {"canonical_name": "Beagle", "canonical_name_ru": "Бигль",
     "species": "dog", "aliases": ["бигл"]},
    {"canonical_name": "Dobermann", "canonical_name_ru": "Доберман",
     "species": "dog", "aliases": ["доберман"]},
    {"canonical_name": "Rottweiler", "canonical_name_ru": "Ротвейлер",
     "species": "dog", "aliases": ["ротвейлер"]},
    {"canonical_name": "Boxer", "canonical_name_ru": "Боксёр",
     "species": "dog", "aliases": ["боксер"]},
    {"canonical_name": "Dalmatian", "canonical_name_ru": "Далматин",
     "species": "dog", "aliases": ["далматинец", "далматин"]},
    {"canonical_name": "Australian Shepherd", "canonical_name_ru": "Австралийская овчарка",
     "species": "dog", "aliases": ["аусси", "австралийская"]},
    {"canonical_name": "Border Collie", "canonical_name_ru": "Бордер-колли",
     "species": "dog", "aliases": ["бордер", "колли", "бордер колли"]},
    {"canonical_name": "Dachshund", "canonical_name_ru": "Такса",
     "species": "dog", "aliases": ["такса"]},
    {"canonical_name": "Maltese", "canonical_name_ru": "Мальтийская болонка",
     "species": "dog", "aliases": ["мальтез", "мальтийская", "болонка"]},
    {"canonical_name": "Samoyed", "canonical_name_ru": "Самоед",
     "species": "dog", "aliases": ["самоед"]},
    {"canonical_name": "Shih Tzu", "canonical_name_ru": "Ши-тцу",
     "species": "dog", "aliases": ["ши тцу", "ши-тцу"]},
    {"canonical_name": "Poodle", "canonical_name_ru": "Пудель",
     "species": "dog", "aliases": ["пудель"]},
    {"canonical_name": "Corgi", "canonical_name_ru": "Корги",
     "species": "dog", "aliases": ["корги", "вельш-корги", "вельш корги"]},
    {"canonical_name": "English Bulldog", "canonical_name_ru": "Английский бульдог",
     "species": "dog", "aliases": ["английский бульдог", "бульдог"]},
    {"canonical_name": "Alaskan Malamute", "canonical_name_ru": "Аляскинский маламут",
     "species": "dog", "aliases": ["маламут", "аляскинский"]},
    # --- CATS ---
    {"canonical_name": "British Shorthair", "canonical_name_ru": "Британская короткошёрстная",
     "species": "cat", "aliases": ["британец", "британская", "британец кот"]},
    {"canonical_name": "Scottish Fold", "canonical_name_ru": "Шотландская вислоухая",
     "species": "cat", "aliases": ["шотландская", "вислоухая", "скоттиш", "вислоухий"]},
    {"canonical_name": "Maine Coon", "canonical_name_ru": "Мейн-кун",
     "species": "cat", "aliases": ["мейн кун", "мейнкун", "main coon"]},
    {"canonical_name": "Persian", "canonical_name_ru": "Персидская",
     "species": "cat", "aliases": ["перс", "персидский", "персидская"]},
    {"canonical_name": "Bengal", "canonical_name_ru": "Бенгальская",
     "species": "cat", "aliases": ["бенгал", "бенгальский"]},
    {"canonical_name": "Siamese", "canonical_name_ru": "Сиамская",
     "species": "cat", "aliases": ["сиамский", "сиамская"]},
    {"canonical_name": "Sphynx", "canonical_name_ru": "Сфинкс",
     "species": "cat", "aliases": ["сфинкс", "sphinx"]},
    {"canonical_name": "Russian Blue", "canonical_name_ru": "Русская голубая",
     "species": "cat", "aliases": ["русская голубая", "голубая"]},
    {"canonical_name": "Ragdoll", "canonical_name_ru": "Рэгдолл",
     "species": "cat", "aliases": ["рагдол", "рэгдол"]},
    {"canonical_name": "Abyssinian", "canonical_name_ru": "Абиссинская",
     "species": "cat", "aliases": ["абиссинец", "абиссинская"]},
    {"canonical_name": "Norwegian Forest Cat", "canonical_name_ru": "Норвежская лесная",
     "species": "cat", "aliases": ["норвежская", "норвежская лесная"]},
    {"canonical_name": "Burmese", "canonical_name_ru": "Бурманская",
     "species": "cat", "aliases": ["бурма", "бурманская"]},
    {"canonical_name": "Turkish Angora", "canonical_name_ru": "Турецкая ангора",
     "species": "cat", "aliases": ["ангора", "турецкая"]},
    {"canonical_name": "Exotic Shorthair", "canonical_name_ru": "Экзотическая короткошёрстная",
     "species": "cat", "aliases": ["экзот", "экзотик", "экзотическая"]},
    {"canonical_name": "Cornish Rex", "canonical_name_ru": "Корниш-рекс",
     "species": "cat", "aliases": ["корниш", "корниш рекс"]},
    {"canonical_name": "Ragdoll", "canonical_name_ru": "Рэгдолл",
     "species": "cat", "aliases": ["рагдол", "рэгдол", "рэгдолл"]},
    {"canonical_name": "Birman", "canonical_name_ru": "Бирманская",
     "species": "cat", "aliases": ["бирма", "бирманская", "священная бирма"]},
    {"canonical_name": "Devon Rex", "canonical_name_ru": "Девон-рекс",
     "species": "cat", "aliases": ["девон", "девон рекс"]},
    {"canonical_name": "Siberian", "canonical_name_ru": "Сибирская",
     "species": "cat", "aliases": ["сибирская", "сибирский"]},
    {"canonical_name": "Oriental Shorthair", "canonical_name_ru": "Ориентальная",
     "species": "cat", "aliases": ["ориентал", "ориентальная", "ориент"]},
    {"canonical_name": "American Shorthair", "canonical_name_ru": "Американская короткошёрстная",
     "species": "cat", "aliases": ["американская", "американец", "american shorthair"]},
    {"canonical_name": "Tonkinese", "canonical_name_ru": "Тонкинская",
     "species": "cat", "aliases": ["тонкин", "тонкинская"]},
]


async def seed():
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    engine = create_async_engine(
        settings.async_database_url, connect_args={"ssl": ssl_ctx}
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        for data in BREEDS:
            session.add(BreedRegistry(**data))
        await session.commit()
    await engine.dispose()
    print(f"Breed seed complete: {len(BREEDS)} breeds inserted")


if __name__ == "__main__":
    asyncio.run(seed())
