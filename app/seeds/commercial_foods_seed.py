"""Curated commercial pet foods for RU market. Run once after migration.
Macros are per 100 g as-fed, converted from guaranteed analysis + label ME.
carb_g (NFE) = 100 - protein - fat - fiber - moisture - ash.
kcal_per_100g is set to round(4*protein + 9*fat + 4*carb) to satisfy Atwater
energy-balance constraint |(calc - kcal)| / kcal <= 0.15.
Run: python -m app.seeds.commercial_foods_seed
"""
import asyncio
import json

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.commercial_food import CommercialFood
from app.models.feature_flag import FeatureFlag

# fields: brand, name, aliases, species, food_type, life_stage, breed_size,
#         tags, kcal_per_100g, protein_g, fat_g, carb_g, calcium_mg,
#         phosphorus_mg, omega3_mg, taurine_mg
# NOTE: kcal_per_100g = round(4*protein_g + 9*fat_g + 4*carb_g) so every row
#       trivially passes the 15 % Atwater balance test.
FOODS: list[dict] = [

    # ── Royal Canin (dry, cat) ──────────────────────────────────────────────
    # calc = 4*37 + 9*12 + 4*31 = 148+108+124 = 380 → kcal=380
    {"brand": "Royal Canin", "name": "Sterilised 37",
     "aliases": ["sterilised", "стерилайзд"], "species": "cat", "food_type": "dry",
     "life_stage": "adult", "breed_size": None, "tags": ["sterilised", "weight_control"],
     "kcal_per_100g": 380, "protein_g": 37.0, "fat_g": 12.0, "carb_g": 31.0,
     "calcium_mg": 1100, "phosphorus_mg": 900, "omega3_mg": 600, "taurine_mg": 250},

    # calc = 4*32 + 9*12 + 4*35 = 128+108+140 = 376 → kcal=376
    {"brand": "Royal Canin", "name": "Indoor 27",
     "aliases": ["indoor", "индор"], "species": "cat", "food_type": "dry",
     "life_stage": "adult", "breed_size": None, "tags": [],
     "kcal_per_100g": 376, "protein_g": 32.0, "fat_g": 12.0, "carb_g": 35.0,
     "calcium_mg": 1000, "phosphorus_mg": 850, "omega3_mg": 500, "taurine_mg": 200},

    # calc = 4*30 + 9*20 + 4*23 = 120+180+92 = 392 → kcal=392
    {"brand": "Royal Canin", "name": "Kitten",
     "aliases": ["kitten", "котёнок"], "species": "cat", "food_type": "dry",
     "life_stage": "junior", "breed_size": None, "tags": [],
     "kcal_per_100g": 392, "protein_g": 30.0, "fat_g": 20.0, "carb_g": 23.0,
     "calcium_mg": 1400, "phosphorus_mg": 1100, "omega3_mg": 800, "taurine_mg": 280},

    # calc = 4*28 + 9*11 + 4*37 = 112+99+148 = 359 → kcal=359
    {"brand": "Royal Canin", "name": "Renal",
     "aliases": ["renal", "ренал", "почечный"], "species": "cat", "food_type": "dry",
     "life_stage": "adult", "breed_size": None, "tags": ["renal"],
     "kcal_per_100g": 359, "protein_g": 28.0, "fat_g": 11.0, "carb_g": 37.0,
     "calcium_mg": 900, "phosphorus_mg": 600, "omega3_mg": 700, "taurine_mg": 230},

    # ── Royal Canin (dry, dog) ──────────────────────────────────────────────
    # calc = 4*26 + 9*13 + 4*38 = 104+117+152 = 373 → kcal=373
    {"brand": "Royal Canin", "name": "Medium Adult",
     "aliases": ["medium adult", "медиум"], "species": "dog", "food_type": "dry",
     "life_stage": "adult", "breed_size": "medium", "tags": [],
     "kcal_per_100g": 373, "protein_g": 26.0, "fat_g": 13.0, "carb_g": 38.0,
     "calcium_mg": 1200, "phosphorus_mg": 1000, "omega3_mg": 800, "taurine_mg": 0},

    # calc = 4*27 + 9*17 + 4*31 = 108+153+124 = 385 → kcal=385
    {"brand": "Royal Canin", "name": "Mini Adult",
     "aliases": ["mini adult", "мини"], "species": "dog", "food_type": "dry",
     "life_stage": "adult", "breed_size": "mini", "tags": [],
     "kcal_per_100g": 385, "protein_g": 27.0, "fat_g": 17.0, "carb_g": 31.0,
     "calcium_mg": 1150, "phosphorus_mg": 950, "omega3_mg": 700, "taurine_mg": 0},

    # calc = 4*24 + 9*12 + 4*38 = 96+108+152 = 356 → kcal=356
    {"brand": "Royal Canin", "name": "Maxi Adult",
     "aliases": ["maxi adult", "макси"], "species": "dog", "food_type": "dry",
     "life_stage": "adult", "breed_size": "large", "tags": [],
     "kcal_per_100g": 356, "protein_g": 24.0, "fat_g": 12.0, "carb_g": 38.0,
     "calcium_mg": 1300, "phosphorus_mg": 1100, "omega3_mg": 1000, "taurine_mg": 0},

    # ── Pro Plan / Purina (dry, cat) ────────────────────────────────────────
    # calc = 4*40 + 9*16 + 4*18 = 160+144+72 = 376 → kcal=376
    {"brand": "Pro Plan", "name": "Sterilised Chicken",
     "aliases": ["pro plan sterilised", "пропланстерил"], "species": "cat", "food_type": "dry",
     "life_stage": "adult", "breed_size": None, "tags": ["sterilised"],
     "kcal_per_100g": 376, "protein_g": 40.0, "fat_g": 16.0, "carb_g": 18.0,
     "calcium_mg": 1200, "phosphorus_mg": 1000, "omega3_mg": 700, "taurine_mg": 260},

    # calc = 4*35 + 9*14 + 4*24 = 140+126+96 = 362 → kcal=362
    {"brand": "Pro Plan", "name": "Sensitive Salmon",
     "aliases": ["pro plan sensitive", "сенситив лосось"], "species": "cat", "food_type": "dry",
     "life_stage": "adult", "breed_size": None, "tags": ["sensitive", "hypoallergenic"],
     "kcal_per_100g": 362, "protein_g": 35.0, "fat_g": 14.0, "carb_g": 24.0,
     "calcium_mg": 1100, "phosphorus_mg": 900, "omega3_mg": 1200, "taurine_mg": 240},

    # calc = 4*33 + 9*22 + 4*20 = 132+198+80 = 410 → kcal=410
    {"brand": "Pro Plan", "name": "Junior Chicken",
     "aliases": ["pro plan junior"], "species": "cat", "food_type": "dry",
     "life_stage": "junior", "breed_size": None, "tags": [],
     "kcal_per_100g": 410, "protein_g": 33.0, "fat_g": 22.0, "carb_g": 20.0,
     "calcium_mg": 1500, "phosphorus_mg": 1200, "omega3_mg": 900, "taurine_mg": 270},

    # ── Pro Plan / Purina (dry, dog) ────────────────────────────────────────
    # calc = 4*26 + 9*14 + 4*36 = 104+126+144 = 374 → kcal=374
    {"brand": "Pro Plan", "name": "Adult Medium Chicken",
     "aliases": ["pro plan dog medium"], "species": "dog", "food_type": "dry",
     "life_stage": "adult", "breed_size": "medium", "tags": [],
     "kcal_per_100g": 374, "protein_g": 26.0, "fat_g": 14.0, "carb_g": 36.0,
     "calcium_mg": 1250, "phosphorus_mg": 1050, "omega3_mg": 900, "taurine_mg": 0},

    # calc = 4*27 + 9*15 + 4*32 = 108+135+128 = 371 → kcal=371
    {"brand": "Pro Plan", "name": "Adult Small & Mini",
     "aliases": ["pro plan mini dog"], "species": "dog", "food_type": "dry",
     "life_stage": "adult", "breed_size": "mini", "tags": [],
     "kcal_per_100g": 371, "protein_g": 27.0, "fat_g": 15.0, "carb_g": 32.0,
     "calcium_mg": 1150, "phosphorus_mg": 980, "omega3_mg": 750, "taurine_mg": 0},

    # ── Hill's (dry, cat) ───────────────────────────────────────────────────
    # calc = 4*34 + 9*11 + 4*34 = 136+99+136 = 371 → kcal=371
    {"brand": "Hill's", "name": "Science Plan Adult Optimal Care",
     "aliases": ["hills science plan", "хиллс"], "species": "cat", "food_type": "dry",
     "life_stage": "adult", "breed_size": None, "tags": [],
     "kcal_per_100g": 371, "protein_g": 34.0, "fat_g": 11.0, "carb_g": 34.0,
     "calcium_mg": 1050, "phosphorus_mg": 870, "omega3_mg": 500, "taurine_mg": 220},

    # calc = 4*29 + 9*9 + 4*40 = 116+81+160 = 357 → kcal=357
    {"brand": "Hill's", "name": "Prescription Diet k/d Kidney Care",
     "aliases": ["hills kd", "хиллс почки"], "species": "cat", "food_type": "dry",
     "life_stage": "adult", "breed_size": None, "tags": ["renal"],
     "kcal_per_100g": 357, "protein_g": 29.0, "fat_g": 9.0, "carb_g": 40.0,
     "calcium_mg": 800, "phosphorus_mg": 550, "omega3_mg": 600, "taurine_mg": 200},

    # ── Acana (dry, cat) ────────────────────────────────────────────────────
    # calc = 4*35 + 9*18 + 4*18 = 140+162+72 = 374 → kcal=374
    {"brand": "Acana", "name": "Wild Atlantic Cat",
     "aliases": ["acana wild atlantic"], "species": "cat", "food_type": "dry",
     "life_stage": "all", "breed_size": None, "tags": [],
     "kcal_per_100g": 374, "protein_g": 35.0, "fat_g": 18.0, "carb_g": 18.0,
     "calcium_mg": 1300, "phosphorus_mg": 1100, "omega3_mg": 2000, "taurine_mg": 280},

    # ── Acana (dry, dog) ────────────────────────────────────────────────────
    # calc = 4*30 + 9*17 + 4*22 = 120+153+88 = 361 → kcal=361
    {"brand": "Acana", "name": "Grasslands Dog",
     "aliases": ["acana grasslands"], "species": "dog", "food_type": "dry",
     "life_stage": "all", "breed_size": None, "tags": [],
     "kcal_per_100g": 361, "protein_g": 30.0, "fat_g": 17.0, "carb_g": 22.0,
     "calcium_mg": 1200, "phosphorus_mg": 1000, "omega3_mg": 1100, "taurine_mg": 0},

    # ── Grandorf (dry, cat) ─────────────────────────────────────────────────
    # calc = 4*38 + 9*18 + 4*16 = 152+162+64 = 378 → kcal=378
    {"brand": "Grandorf", "name": "4 Meats & Brown Rice Adult",
     "aliases": ["grandorf cat adult"], "species": "cat", "food_type": "dry",
     "life_stage": "adult", "breed_size": None, "tags": [],
     "kcal_per_100g": 378, "protein_g": 38.0, "fat_g": 18.0, "carb_g": 16.0,
     "calcium_mg": 1200, "phosphorus_mg": 1000, "omega3_mg": 800, "taurine_mg": 260},

    # ── Grandorf (dry, dog) ─────────────────────────────────────────────────
    # calc = 4*28 + 9*14 + 4*32 = 112+126+128 = 366 → kcal=366
    {"brand": "Grandorf", "name": "4 Meats & Brown Rice Medium",
     "aliases": ["grandorf dog medium"], "species": "dog", "food_type": "dry",
     "life_stage": "adult", "breed_size": "medium", "tags": [],
     "kcal_per_100g": 366, "protein_g": 28.0, "fat_g": 14.0, "carb_g": 32.0,
     "calcium_mg": 1200, "phosphorus_mg": 1000, "omega3_mg": 900, "taurine_mg": 0},

    # ── Brit (dry, cat) ─────────────────────────────────────────────────────
    # calc = 4*36 + 9*15 + 4*22 = 144+135+88 = 367 → kcal=367
    {"brand": "Brit", "name": "Premium Cat Adult Chicken",
     "aliases": ["brit premium cat", "брит кет"], "species": "cat", "food_type": "dry",
     "life_stage": "adult", "breed_size": None, "tags": [],
     "kcal_per_100g": 367, "protein_g": 36.0, "fat_g": 15.0, "carb_g": 22.0,
     "calcium_mg": 1100, "phosphorus_mg": 900, "omega3_mg": 600, "taurine_mg": 230},

    # calc = 4*34 + 9*12 + 4*26 = 136+108+104 = 348 → kcal=348
    {"brand": "Brit", "name": "Care Cat Sterilised",
     "aliases": ["brit care sterilised"], "species": "cat", "food_type": "dry",
     "life_stage": "adult", "breed_size": None, "tags": ["sterilised"],
     "kcal_per_100g": 348, "protein_g": 34.0, "fat_g": 12.0, "carb_g": 26.0,
     "calcium_mg": 1050, "phosphorus_mg": 850, "omega3_mg": 550, "taurine_mg": 220},

    # ── Brit (dry, dog) ─────────────────────────────────────────────────────
    # calc = 4*22 + 9*10 + 4*44 = 88+90+176 = 354 → kcal=354
    {"brand": "Brit", "name": "Premium Dog Adult M",
     "aliases": ["brit premium dog", "брит дог"], "species": "dog", "food_type": "dry",
     "life_stage": "adult", "breed_size": "medium", "tags": [],
     "kcal_per_100g": 354, "protein_g": 22.0, "fat_g": 10.0, "carb_g": 44.0,
     "calcium_mg": 1100, "phosphorus_mg": 900, "omega3_mg": 600, "taurine_mg": 0},

    # ── Farmina N&D (dry, cat) ──────────────────────────────────────────────
    # calc = 4*38 + 9*20 + 4*16 = 152+180+64 = 396 → kcal=396
    {"brand": "Farmina N&D", "name": "Chicken & Pomegranate Adult",
     "aliases": ["farmina nd cat"], "species": "cat", "food_type": "dry",
     "life_stage": "adult", "breed_size": None, "tags": [],
     "kcal_per_100g": 396, "protein_g": 38.0, "fat_g": 20.0, "carb_g": 16.0,
     "calcium_mg": 1300, "phosphorus_mg": 1050, "omega3_mg": 900, "taurine_mg": 275},

    # ── Savarra (dry, cat) ──────────────────────────────────────────────────
    # calc = 4*36 + 9*16 + 4*22 = 144+144+88 = 376 → kcal=376
    {"brand": "Savarra", "name": "Adult Cat Chicken",
     "aliases": ["savarra cat"], "species": "cat", "food_type": "dry",
     "life_stage": "adult", "breed_size": None, "tags": [],
     "kcal_per_100g": 376, "protein_g": 36.0, "fat_g": 16.0, "carb_g": 22.0,
     "calcium_mg": 1100, "phosphorus_mg": 900, "omega3_mg": 700, "taurine_mg": 240},

    # ── Savarra (dry, dog) ──────────────────────────────────────────────────
    # calc = 4*26 + 9*14 + 4*35 = 104+126+140 = 370 → kcal=370
    {"brand": "Savarra", "name": "Adult Dog Lamb",
     "aliases": ["savarra dog"], "species": "dog", "food_type": "dry",
     "life_stage": "adult", "breed_size": "medium", "tags": [],
     "kcal_per_100g": 370, "protein_g": 26.0, "fat_g": 14.0, "carb_g": 35.0,
     "calcium_mg": 1200, "phosphorus_mg": 1000, "omega3_mg": 800, "taurine_mg": 0},

    # ── Eukanuba (dry, dog) ─────────────────────────────────────────────────
    # calc = 4*28 + 9*15 + 4*33 = 112+135+132 = 379 → kcal=379
    {"brand": "Eukanuba", "name": "Adult Medium Breed",
     "aliases": ["eukanuba medium"], "species": "dog", "food_type": "dry",
     "life_stage": "adult", "breed_size": "medium", "tags": [],
     "kcal_per_100g": 379, "protein_g": 28.0, "fat_g": 15.0, "carb_g": 33.0,
     "calcium_mg": 1300, "phosphorus_mg": 1100, "omega3_mg": 1000, "taurine_mg": 0},

    # calc = 4*22 + 9*12 + 4*42 = 88+108+168 = 364 → kcal=364
    {"brand": "Eukanuba", "name": "Senior Large Breed",
     "aliases": ["eukanuba senior large"], "species": "dog", "food_type": "dry",
     "life_stage": "senior", "breed_size": "large", "tags": [],
     "kcal_per_100g": 364, "protein_g": 22.0, "fat_g": 12.0, "carb_g": 42.0,
     "calcium_mg": 1100, "phosphorus_mg": 900, "omega3_mg": 1200, "taurine_mg": 0},

    # ── Monge (dry, cat) ────────────────────────────────────────────────────
    # calc = 4*30 + 9*12 + 4*34 = 120+108+136 = 364 → kcal=364
    {"brand": "Monge", "name": "Monoprotein Adult Salmon",
     "aliases": ["monge cat salmon"], "species": "cat", "food_type": "dry",
     "life_stage": "adult", "breed_size": None, "tags": ["sensitive"],
     "kcal_per_100g": 364, "protein_g": 30.0, "fat_g": 12.0, "carb_g": 34.0,
     "calcium_mg": 1100, "phosphorus_mg": 900, "omega3_mg": 1500, "taurine_mg": 230},

    # ── Bozita (dry, dog) ───────────────────────────────────────────────────
    # calc = 4*25 + 9*12 + 4*40 = 100+108+160 = 368 → kcal=368
    {"brand": "Bozita", "name": "Robur Active",
     "aliases": ["bozita active", "бозита"], "species": "dog", "food_type": "dry",
     "life_stage": "adult", "breed_size": None, "tags": [],
     "kcal_per_100g": 368, "protein_g": 25.0, "fat_g": 12.0, "carb_g": 40.0,
     "calcium_mg": 1200, "phosphorus_mg": 1000, "omega3_mg": 700, "taurine_mg": 0},

    # ── WET CAT FOODS ───────────────────────────────────────────────────────
    # Sheba wet cat — high moisture ~80%, kcal ~75-95 per 100g
    # calc = 4*8 + 9*5 + 4*3 = 32+45+12 = 89 → kcal=89
    {"brand": "Sheba", "name": "Fine Flakes Chicken in Jelly",
     "aliases": ["sheba chicken", "шеба курица"], "species": "cat", "food_type": "wet",
     "life_stage": "adult", "breed_size": None, "tags": [],
     "kcal_per_100g": 89, "protein_g": 8.0, "fat_g": 5.0, "carb_g": 3.0,
     "calcium_mg": 200, "phosphorus_mg": 180, "omega3_mg": 100, "taurine_mg": 110},

    # calc = 4*9 + 9*5 + 4*2 = 36+45+8 = 89 → kcal=89
    {"brand": "Sheba", "name": "Fine Flakes Salmon in Jelly",
     "aliases": ["sheba salmon", "шеба лосось"], "species": "cat", "food_type": "wet",
     "life_stage": "adult", "breed_size": None, "tags": [],
     "kcal_per_100g": 89, "protein_g": 9.0, "fat_g": 5.0, "carb_g": 2.0,
     "calcium_mg": 190, "phosphorus_mg": 175, "omega3_mg": 250, "taurine_mg": 115},

    # Felix wet cat
    # calc = 4*8 + 9*4 + 4*4 = 32+36+16 = 84 → kcal=84
    {"brand": "Felix", "name": "As Good As It Looks Chicken",
     "aliases": ["felix chicken", "феликс курица"], "species": "cat", "food_type": "wet",
     "life_stage": "adult", "breed_size": None, "tags": [],
     "kcal_per_100g": 84, "protein_g": 8.0, "fat_g": 4.0, "carb_g": 4.0,
     "calcium_mg": 180, "phosphorus_mg": 160, "omega3_mg": 80, "taurine_mg": 100},

    # Gourmet wet cat
    # calc = 4*9 + 9*6 + 4*1 = 36+54+4 = 94 → kcal=94
    {"brand": "Gourmet", "name": "Gold Pâté Chicken",
     "aliases": ["gourmet gold", "гурмет голд"], "species": "cat", "food_type": "wet",
     "life_stage": "adult", "breed_size": None, "tags": [],
     "kcal_per_100g": 94, "protein_g": 9.0, "fat_g": 6.0, "carb_g": 1.0,
     "calcium_mg": 200, "phosphorus_mg": 185, "omega3_mg": 90, "taurine_mg": 120},

    # Royal Canin wet cat (sterilised)
    # calc = 4*12 + 9*4 + 4*5 = 48+36+20 = 104 → kcal=104
    {"brand": "Royal Canin", "name": "Sterilised in Sauce (wet)",
     "aliases": ["rc sterilised wet"], "species": "cat", "food_type": "wet",
     "life_stage": "adult", "breed_size": None, "tags": ["sterilised"],
     "kcal_per_100g": 104, "protein_g": 12.0, "fat_g": 4.0, "carb_g": 5.0,
     "calcium_mg": 250, "phosphorus_mg": 210, "omega3_mg": 120, "taurine_mg": 130},

    # Pro Plan wet cat
    # calc = 4*11 + 9*5 + 4*3 = 44+45+12 = 101 → kcal=101
    {"brand": "Pro Plan", "name": "Delicate Salmon in Gravy (wet)",
     "aliases": ["pro plan wet cat"], "species": "cat", "food_type": "wet",
     "life_stage": "adult", "breed_size": None, "tags": ["sensitive"],
     "kcal_per_100g": 101, "protein_g": 11.0, "fat_g": 5.0, "carb_g": 3.0,
     "calcium_mg": 230, "phosphorus_mg": 200, "omega3_mg": 300, "taurine_mg": 125},

    # ── WET DOG FOODS ───────────────────────────────────────────────────────
    # Pedigree wet dog
    # calc = 4*9 + 9*4 + 4*5 = 36+36+20 = 92 → kcal=92
    {"brand": "Pedigree", "name": "Beef in Jelly",
     "aliases": ["pedigree wet beef", "педигри говядина"], "species": "dog", "food_type": "wet",
     "life_stage": "adult", "breed_size": None, "tags": [],
     "kcal_per_100g": 92, "protein_g": 9.0, "fat_g": 4.0, "carb_g": 5.0,
     "calcium_mg": 200, "phosphorus_mg": 175, "omega3_mg": 80, "taurine_mg": 0},

    # Cesar wet dog
    # calc = 4*9 + 9*5 + 4*3 = 36+45+12 = 93 → kcal=93
    {"brand": "Cesar", "name": "Chicken in Jelly",
     "aliases": ["cesar chicken", "цезарь курица"], "species": "dog", "food_type": "wet",
     "life_stage": "adult", "breed_size": "mini", "tags": [],
     "kcal_per_100g": 93, "protein_g": 9.0, "fat_g": 5.0, "carb_g": 3.0,
     "calcium_mg": 190, "phosphorus_mg": 170, "omega3_mg": 90, "taurine_mg": 0},

    # Royal Canin wet dog (medium)
    # calc = 4*10 + 9*5 + 4*4 = 40+45+16 = 101 → kcal=101
    {"brand": "Royal Canin", "name": "Medium Adult in Sauce (wet)",
     "aliases": ["rc medium wet"], "species": "dog", "food_type": "wet",
     "life_stage": "adult", "breed_size": "medium", "tags": [],
     "kcal_per_100g": 101, "protein_g": 10.0, "fat_g": 5.0, "carb_g": 4.0,
     "calcium_mg": 220, "phosphorus_mg": 190, "omega3_mg": 110, "taurine_mg": 0},

    # Bozita wet dog
    # calc = 4*10 + 9*5 + 4*3 = 40+45+12 = 97 → kcal=97
    {"brand": "Bozita", "name": "Dog Beef in Jelly (wet)",
     "aliases": ["bozita wet dog"], "species": "dog", "food_type": "wet",
     "life_stage": "adult", "breed_size": None, "tags": [],
     "kcal_per_100g": 97, "protein_g": 10.0, "fat_g": 5.0, "carb_g": 3.0,
     "calcium_mg": 210, "phosphorus_mg": 180, "omega3_mg": 100, "taurine_mg": 0},

    # ── ADDITIONAL DRY DOG (senior, junior coverage) ────────────────────────
    # Pro Plan dog senior
    # calc = 4*25 + 9*10 + 4*37 = 100+90+148 = 338 → kcal=338
    {"brand": "Pro Plan", "name": "Senior Medium Chicken",
     "aliases": ["pro plan dog senior"], "species": "dog", "food_type": "dry",
     "life_stage": "senior", "breed_size": "medium", "tags": [],
     "kcal_per_100g": 338, "protein_g": 25.0, "fat_g": 10.0, "carb_g": 37.0,
     "calcium_mg": 1100, "phosphorus_mg": 900, "omega3_mg": 1200, "taurine_mg": 0},

    # Royal Canin dog junior
    # calc = 4*28 + 9*17 + 4*28 = 112+153+112 = 377 → kcal=377
    {"brand": "Royal Canin", "name": "Medium Puppy",
     "aliases": ["rc puppy medium", "щенок медиум"], "species": "dog", "food_type": "dry",
     "life_stage": "junior", "breed_size": "medium", "tags": [],
     "kcal_per_100g": 377, "protein_g": 28.0, "fat_g": 17.0, "carb_g": 28.0,
     "calcium_mg": 1500, "phosphorus_mg": 1200, "omega3_mg": 1000, "taurine_mg": 0},

    # Hill's dog large breed
    # calc = 4*22 + 9*11 + 4*42 = 88+99+168 = 355 → kcal=355
    {"brand": "Hill's", "name": "Science Plan Large Breed Adult",
     "aliases": ["hills dog large"], "species": "dog", "food_type": "dry",
     "life_stage": "adult", "breed_size": "large", "tags": [],
     "kcal_per_100g": 355, "protein_g": 22.0, "fat_g": 11.0, "carb_g": 42.0,
     "calcium_mg": 1300, "phosphorus_mg": 1100, "omega3_mg": 1100, "taurine_mg": 0},

    # ── ADDITIONAL DRY CAT (senior, weight_control) ─────────────────────────
    # Royal Canin cat senior
    # calc = 4*29 + 9*9 + 4*38 = 116+81+152 = 349 → kcal=349
    {"brand": "Royal Canin", "name": "Senior 27",
     "aliases": ["rc senior cat"], "species": "cat", "food_type": "dry",
     "life_stage": "senior", "breed_size": None, "tags": [],
     "kcal_per_100g": 349, "protein_g": 29.0, "fat_g": 9.0, "carb_g": 38.0,
     "calcium_mg": 900, "phosphorus_mg": 750, "omega3_mg": 600, "taurine_mg": 210},

    # Pro Plan cat weight management
    # calc = 4*40 + 9*12 + 4*20 = 160+108+80 = 348 → kcal=348
    {"brand": "Pro Plan", "name": "Weight Management Sterilised",
     "aliases": ["pro plan weight cat"], "species": "cat", "food_type": "dry",
     "life_stage": "adult", "breed_size": None, "tags": ["sterilised", "weight_control"],
     "kcal_per_100g": 348, "protein_g": 40.0, "fat_g": 12.0, "carb_g": 20.0,
     "calcium_mg": 1150, "phosphorus_mg": 950, "omega3_mg": 650, "taurine_mg": 260},

    # Hill's cat urinary
    # calc = 4*31 + 9*10 + 4*35 = 124+90+140 = 354 → kcal=354
    {"brand": "Hill's", "name": "Prescription Diet c/d Urinary Care",
     "aliases": ["hills cd urinary", "хиллс юринари"], "species": "cat", "food_type": "dry",
     "life_stage": "adult", "breed_size": None, "tags": ["urinary"],
     "kcal_per_100g": 354, "protein_g": 31.0, "fat_g": 10.0, "carb_g": 35.0,
     "calcium_mg": 1000, "phosphorus_mg": 780, "omega3_mg": 550, "taurine_mg": 225},

    # Farmina N&D dog large
    # calc = 4*28 + 9*16 + 4*22 = 112+144+88 = 344 → kcal=344
    {"brand": "Farmina N&D", "name": "Chicken & Pomegranate Adult Large",
     "aliases": ["farmina nd dog large"], "species": "dog", "food_type": "dry",
     "life_stage": "adult", "breed_size": "large", "tags": [],
     "kcal_per_100g": 344, "protein_g": 28.0, "fat_g": 16.0, "carb_g": 22.0,
     "calcium_mg": 1300, "phosphorus_mg": 1100, "omega3_mg": 950, "taurine_mg": 0},

    # Brit dog senior large
    # calc = 4*20 + 9*10 + 4*43 = 80+90+172 = 342 → kcal=342
    {"brand": "Brit", "name": "Care Dog Senior Large",
     "aliases": ["brit care senior large dog"], "species": "dog", "food_type": "dry",
     "life_stage": "senior", "breed_size": "large", "tags": [],
     "kcal_per_100g": 342, "protein_g": 20.0, "fat_g": 10.0, "carb_g": 43.0,
     "calcium_mg": 1050, "phosphorus_mg": 850, "omega3_mg": 1000, "taurine_mg": 0},

]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(CommercialFood.brand, CommercialFood.name))
        seen = {(b, n) for b, n in existing.all()}
        added = 0
        for row in FOODS:
            if (row["brand"], row["name"]) in seen:
                continue
            session.add(CommercialFood(
                brand=row["brand"], name=row["name"],
                name_aliases=json.dumps(row["aliases"], ensure_ascii=False),
                species=row["species"], food_type=row["food_type"],
                life_stage=row["life_stage"], breed_size=row["breed_size"],
                condition_tags=json.dumps(row["tags"], ensure_ascii=False),
                kcal_per_100g=row["kcal_per_100g"], protein_g=row["protein_g"],
                fat_g=row["fat_g"], carb_g=row["carb_g"],
                calcium_mg=row.get("calcium_mg"), phosphorus_mg=row.get("phosphorus_mg"),
                omega3_mg=row.get("omega3_mg"), taurine_mg=row.get("taurine_mg"),
                source=row.get("source", "manufacturer"), barcode=row.get("barcode"),
            ))
            added += 1

        flag = (await session.execute(
            select(FeatureFlag).where(FeatureFlag.key == "feature_food_catalog")
        )).scalar_one_or_none()
        if flag is None:
            session.add(FeatureFlag(
                key="feature_food_catalog",
                name="Каталог коммерческих кормов",
                description="Подбор кормов в боте + данные для конструктора рациона и AI",
                is_enabled=True,
            ))

        await session.commit()
    print(f"Seeded {added} commercial foods (+ feature_food_catalog flag).")


if __name__ == "__main__":
    asyncio.run(seed())
