-- ================================================================
-- PetFeed — DDL скрипт v1.0
-- База данных: PostgreSQL 15+
-- ================================================================

-- ── ПОЛЬЗОВАТЕЛИ ─────────────────────────────────────────────────
CREATE TABLE users (
    id                      SERIAL PRIMARY KEY,
    telegram_id             BIGINT          NOT NULL UNIQUE,
    username                VARCHAR(255),
    is_active               BOOLEAN         NOT NULL DEFAULT TRUE,
    ai_requests_today       INTEGER         NOT NULL DEFAULT 0,
    ai_requests_reset_at    TIMESTAMP       NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_telegram_id ON users(telegram_id);

-- ── ПИТОМЦЫ ──────────────────────────────────────────────────────
CREATE TABLE pets (
    id          SERIAL PRIMARY KEY,
    owner_id    INTEGER         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        VARCHAR(100)    NOT NULL,
    species     VARCHAR(50)     NOT NULL,   -- cat, dog, rodent, bird, reptile
    breed       VARCHAR(100),
    age_months  INTEGER         NOT NULL CHECK (age_months >= 0),
    weight_kg   DECIMAL(5,2)    NOT NULL CHECK (weight_kg > 0),
    goal        VARCHAR(50)     NOT NULL DEFAULT 'maintain', -- maintain, lose, gain, growth
    is_active   BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pets_owner_id ON pets(owner_id);
CREATE INDEX idx_pets_species ON pets(species);

-- ── ИСТОРИЯ ВЕСА ─────────────────────────────────────────────────
CREATE TABLE weight_history (
    id          SERIAL PRIMARY KEY,
    pet_id      INTEGER         NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    weight_kg   DECIMAL(5,2)    NOT NULL CHECK (weight_kg > 0),
    recorded_at DATE            NOT NULL DEFAULT CURRENT_DATE,
    created_at  TIMESTAMP       NOT NULL DEFAULT NOW(),
    UNIQUE (pet_id, recorded_at)   -- одна запись в день
);

CREATE INDEX idx_weight_history_pet_id ON weight_history(pet_id);

-- ── РАЦИОНЫ ──────────────────────────────────────────────────────
CREATE TABLE rations (
    id                  SERIAL PRIMARY KEY,
    pet_id              INTEGER     NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    daily_calories      INTEGER     NOT NULL CHECK (daily_calories > 0),
    portion_grams       INTEGER     NOT NULL CHECK (portion_grams > 0),
    feedings_per_day    INTEGER     NOT NULL CHECK (feedings_per_day BETWEEN 1 AND 6),
    goal                VARCHAR(50) NOT NULL,
    notes               TEXT,
    created_at          TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rations_pet_id ON rations(pet_id);

-- ── БАЗА ЗНАНИЙ О ПИТАНИИ ────────────────────────────────────────
CREATE TABLE nutrition_knowledge (
    id              SERIAL PRIMARY KEY,
    species         VARCHAR(50)     NOT NULL,
    breed           VARCHAR(100),               -- NULL = для всех пород
    product_name    VARCHAR(255)    NOT NULL,
    is_allowed      BOOLEAN         NOT NULL,
    danger_level    VARCHAR(20)     CHECK (danger_level IN ('moderate', 'dangerous', 'fatal')),
    reason          TEXT            NOT NULL,
    source_url      VARCHAR(500),
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_nutrition_species ON nutrition_knowledge(species);
CREATE INDEX idx_nutrition_product ON nutrition_knowledge(product_name);
CREATE INDEX idx_nutrition_allowed ON nutrition_knowledge(species, is_allowed);

-- ── НАПОМИНАНИЯ О КОРМЛЕНИИ ──────────────────────────────────────
CREATE TABLE feeding_reminders (
    id              SERIAL PRIMARY KEY,
    pet_id          INTEGER     NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    reminder_time   TIME        NOT NULL,
    timezone        VARCHAR(50) NOT NULL DEFAULT 'Europe/Moscow',
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_feeding_reminders_pet_id ON feeding_reminders(pet_id);
CREATE INDEX idx_feeding_reminders_active ON feeding_reminders(is_active, reminder_time);

-- ── ЖУРНАЛ КОРМЛЕНИЙ ─────────────────────────────────────────────
CREATE TABLE feeding_logs (
    id              SERIAL PRIMARY KEY,
    pet_id          INTEGER     NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    reminder_id     INTEGER     REFERENCES feeding_reminders(id) ON DELETE SET NULL,
    fed_at          TIMESTAMP   NOT NULL DEFAULT NOW(),
    notes           TEXT,
    created_at      TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_feeding_logs_pet_id ON feeding_logs(pet_id);
CREATE INDEX idx_feeding_logs_fed_at ON feeding_logs(fed_at);

-- ── ПАРТНЁРЫ ─────────────────────────────────────────────────────
CREATE TABLE partners (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255)    NOT NULL,
    website_url     VARCHAR(500)    NOT NULL,
    api_url         VARCHAR(500)    NOT NULL,
    api_key_hash    VARCHAR(255)    NOT NULL,
    commission_pct  DECIMAL(5,2)    NOT NULL CHECK (commission_pct BETWEEN 0 AND 100),
    is_active       BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

-- ── ТОВАРЫ ПАРТНЁРОВ ─────────────────────────────────────────────
CREATE TABLE products (
    id              SERIAL PRIMARY KEY,
    partner_id      INTEGER         NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    name            VARCHAR(255)    NOT NULL,
    species         VARCHAR(50)     NOT NULL,
    brand           VARCHAR(100),
    weight_grams    INTEGER         CHECK (weight_grams > 0),
    price           DECIMAL(10,2)   NOT NULL CHECK (price > 0),
    is_available    BOOLEAN         NOT NULL DEFAULT TRUE,
    external_id     VARCHAR(255)    NOT NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    UNIQUE (partner_id, external_id)
);

CREATE INDEX idx_products_partner_id ON products(partner_id);
CREATE INDEX idx_products_species ON products(species);
CREATE INDEX idx_products_available ON products(species, is_available);

-- ── ЗАКАЗЫ ───────────────────────────────────────────────────────
CREATE TABLE orders (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pet_id              INTEGER         NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    product_id          INTEGER         NOT NULL REFERENCES products(id),
    partner_id          INTEGER         NOT NULL REFERENCES partners(id),
    referral_token      VARCHAR(255)    NOT NULL UNIQUE,
    status              VARCHAR(50)     NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'confirmed', 'cancelled')),
    commission_amount   DECIMAL(10,2),
    created_at          TIMESTAMP       NOT NULL DEFAULT NOW(),
    confirmed_at        TIMESTAMP
);

CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_referral_token ON orders(referral_token);
CREATE INDEX idx_orders_status ON orders(status);

-- ── AI ЗАПРОСЫ ────────────────────────────────────────────────────
CREATE TABLE ai_requests (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pet_id      INTEGER     NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    question    TEXT        NOT NULL,
    answer      TEXT        NOT NULL,
    is_cached   BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_requests_user_id ON ai_requests(user_id);
CREATE INDEX idx_ai_requests_created_at ON ai_requests(user_id, created_at);

-- ── FEATURE FLAGS ────────────────────────────────────────────────
CREATE TABLE feature_flags (
    id          SERIAL PRIMARY KEY,
    key         VARCHAR(100)    NOT NULL UNIQUE,
    name        VARCHAR(255)    NOT NULL,
    description TEXT,
    is_enabled  BOOLEAN         NOT NULL DEFAULT TRUE,
    updated_by  VARCHAR(255),
    updated_at  TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_feature_flags_key ON feature_flags(key);

-- ================================================================
-- ТЕСТОВЫЕ ДАННЫЕ
-- ================================================================

INSERT INTO users (telegram_id, username) VALUES
    (123456789, 'ivan_petrov'),
    (987654321, 'anna_sidorova');

INSERT INTO pets (owner_id, name, species, breed, age_months, weight_kg, goal) VALUES
    (1, 'Барсик', 'cat', 'Мейн-кун', 24, 5.20, 'maintain'),
    (1, 'Пушок', 'rodent', 'Шиншилла', 12, 0.55, 'maintain'),
    (2, 'Рекс', 'dog', 'Лабрадор', 36, 28.50, 'lose');

INSERT INTO nutrition_knowledge (species, product_name, is_allowed, danger_level, reason) VALUES
    ('cat', 'Лук', FALSE, 'dangerous', 'Вызывает анемию, поражает эритроциты'),
    ('cat', 'Шоколад', FALSE, 'fatal', 'Теобромин токсичен для кошек'),
    ('cat', 'Куриная грудка варёная', TRUE, NULL, 'Легкоусвояемый белок, рекомендован'),
    ('dog', 'Виноград', FALSE, 'fatal', 'Вызывает острую почечную недостаточность'),
    ('dog', 'Говядина варёная', TRUE, NULL, 'Высокобелковый продукт, хорошо усваивается'),
    ('rodent', 'Цитрусовые', FALSE, 'moderate', 'Высокая кислотность раздражает ЖКТ'),
    ('rodent', 'Сено тимофеевки', TRUE, NULL, 'Основа рациона, богато клетчаткой');

INSERT INTO partners (name, website_url, api_url, api_key_hash, commission_pct, is_active) VALUES
    ('ZooShop Test', 'https://zooshop.example.com', 'https://api.zooshop.example.com', 'hashed_key_1', 10.00, TRUE);
