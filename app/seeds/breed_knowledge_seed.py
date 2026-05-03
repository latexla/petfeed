"""
Seed breed knowledge from markdown files.
Run: railway run python3.12 -m app.seeds.breed_knowledge_seed
"""
import asyncio
import re
import ssl
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings
from app.models.breed_knowledge import BreedKnowledge

FILES_DIR = Path(__file__).parent.parent.parent / "Нормы кормления" / "files"


def _parse_breed_file(path: Path, canonical_name: str, species: str = "dog") -> dict:
    content = path.read_text(encoding="utf-8")
    lines = content.split("\n")

    # Auto-detect species from file header
    for line in lines[:5]:
        if "(кошки)" in line or "(кошка)" in line:
            species = "cat"
            break

    canonical_name_ru = canonical_name
    for line in lines[:5]:
        if line.startswith("# "):
            m = re.match(r"^# (.+?) —", line)
            if m:
                canonical_name_ru = m.group(1)
            break

    weight_range = None
    for line in lines:
        if "Масса тела:" in line:
            m = re.search(r"\*\*(.+?)\*\*", line)
            if m:
                weight_range = m.group(1)
            break

    key_risks = None
    for line in lines:
        if "Ключев" in line and "риск" in line and "питания" in line:
            cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
            cleaned = re.sub(r"^[-\s*]+", "", cleaned)
            for prefix in ("Ключевые породные риски питания: ",
                           "Ключевой породный риск питания: "):
                cleaned = cleaned.replace(prefix, "")
            key_risks = cleaned.strip()
            break

    adult_meals = 2
    for line in lines:
        if ("От 1 года" in line or ("Взрослые" in line and "|" in line)) and "раз" in line:
            cells = [c.strip() for c in line.split("|") if c.strip()]
            last = cells[-1] if cells else ""
            m = re.search(r"(\d+)", last)
            if m:
                adult_meals = int(m.group(1))
            break

    return {
        "canonical_name": canonical_name,
        "canonical_name_ru": canonical_name_ru,
        "species": species,
        "weight_range": weight_range,
        "key_risks": key_risks,
        "adult_meals_per_day": adult_meals,
        "full_content": content,
    }


def _build_records() -> list[dict]:
    records = []

    general_path = FILES_DIR / "00_ОБЩИЙ_Токсикология_и_нутрициология.md"
    records.append({
        "canonical_name": "GENERAL_TOXICOLOGY",
        "canonical_name_ru": "Общая токсикология и нутрициология",
        "species": "dog",
        "weight_range": None,
        "key_risks": "Уровень 1: абсолютные токсины. Уровень 2: нутрициологически нежелательные продукты.",
        "adult_meals_per_day": None,
        "full_content": general_path.read_text(encoding="utf-8"),
    })

    breed_map = {
        # Dogs
        "02_Labrador_Retriever.md":  ("Labrador Retriever",        "dog"),
        "03_German_Shepherd.md":     ("German Shepherd",           "dog"),
        "04_French_Bulldog.md":      ("French Bulldog",            "dog"),
        "05_Siberian_Husky.md":      ("Siberian Husky",            "dog"),
        "06_Golden_Retriever.md":    ("Golden Retriever",          "dog"),
        "07_Yorkshire_Terrier.md":   ("Yorkshire Terrier",         "dog"),
        "08_Chihuahua.md":           ("Chihuahua",                 "dog"),
        "09_Pug.md":                 ("Pug",                       "dog"),
        "10_Pomeranian.md":          ("Pomeranian",                "dog"),
        "11_Beagle.md":              ("Beagle",                    "dog"),
        "12_Dobermann.md":           ("Dobermann",                 "dog"),
        "13_Rottweiler.md":          ("Rottweiler",                "dog"),
        "14_Boxer.md":               ("Boxer",                     "dog"),
        "15_Dalmatian.md":           ("Dalmatian",                 "dog"),
        "16_Australian_Shepherd.md": ("Australian Shepherd",       "dog"),
        "17_Border_Collie.md":       ("Border Collie",             "dog"),
        "18_Dachshund.md":           ("Dachshund",                 "dog"),
        "19_Maltese.md":             ("Maltese",                   "dog"),
        "20_Samoyed.md":             ("Samoyed",                   "dog"),
        "21_Shih_Tzu.md":            ("Shih Tzu",                  "dog"),
        "22_Poodle.md":              ("Poodle",                    "dog"),
        "23_Corgi.md":               ("Corgi",                     "dog"),
        "24_English_Bulldog.md":     ("English Bulldog",           "dog"),
        "25_Alaskan_Malamute.md":    ("Alaskan Malamute",          "dog"),
        # Cats
        "26_Persian.md":             ("Persian",                   "cat"),
        "27_Maine_Coon.md":          ("Maine Coon",                "cat"),
        "28_Ragdoll.md":             ("Ragdoll",                   "cat"),
        "29_British_Shorthair.md":   ("British Shorthair",         "cat"),
        "30_Siamese.md":             ("Siamese",                   "cat"),
        "31_Scottish_Fold.md":       ("Scottish Fold",             "cat"),
        "32_Sphynx.md":              ("Sphynx",                    "cat"),
        "33_Bengal.md":              ("Bengal",                    "cat"),
        "34_Russian_Blue.md":        ("Russian Blue",              "cat"),
        "35_Norwegian_Forest_Cat.md":("Norwegian Forest Cat",      "cat"),
        "36_Abyssinian.md":          ("Abyssinian",                "cat"),
        "37_Devon_Rex.md":           ("Devon Rex",                 "cat"),
        "38_Birman.md":              ("Birman",                    "cat"),
        "39_Burmese.md":             ("Burmese",                   "cat"),
        "40_Turkish_Angora.md":      ("Turkish Angora",            "cat"),
        "41_Oriental_Shorthair.md":  ("Oriental Shorthair",        "cat"),
        "42_Exotic_Shorthair.md":    ("Exotic Shorthair",          "cat"),
        "43_American_Shorthair.md":  ("American Shorthair",        "cat"),
        "44_Siberian.md":            ("Siberian",                  "cat"),
        "45_Tonkinese.md":           ("Tonkinese",                 "cat"),
    }

    for fname, (canonical_name, species) in breed_map.items():
        path = FILES_DIR / fname
        records.append(_parse_breed_file(path, canonical_name, species))

    return records


async def seed():
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    engine = create_async_engine(
        settings.async_database_url, connect_args={"ssl": ssl_ctx}
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    records = _build_records()
    async with session_factory() as session:
        for data in records:
            session.add(BreedKnowledge(**data))
        await session.commit()
    await engine.dispose()
    print(f"Breed knowledge seed complete: {len(records)} records inserted")
    for r in records:
        print(f"  [{r['species']}] {r['canonical_name']} — {r['adult_meals_per_day']} meals/day")


if __name__ == "__main__":
    asyncio.run(seed())
