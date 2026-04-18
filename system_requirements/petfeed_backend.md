# Backend логика — PetFeed v1.0

---

## BL-001: Регистрация пользователя и создание профиля питомца

### 1. Общий обзор
При первом обращении пользователя через Telegram-бота система автоматически создаёт пользователя и запускает пошаговый диалог создания профиля питомца. Связан с UC-001, US-001.

### 2. Входные данные

| Параметр | Тип | Ограничения |
|---|---|---|
| `telegram_id` | bigint | Обязательный, уникальный |
| `username` | string | Опциональный, max 255 символов |
| `species` | string | Enum: cat, dog, rodent, bird, reptile |
| `breed` | string | Опциональный, max 100 символов |
| `name` | string | Обязательный, max 100 символов |
| `age_months` | int | Обязательный, >= 0 |
| `weight_kg` | decimal | Обязательный, > 0, max 999.99 |
| `goal` | string | Enum: maintain, lose, gain, growth |

### 3. Валидации

- **Структурные:** `age_months` — целое число >= 0; `weight_kg` — положительное decimal(5,2)
- **Бизнес-правила:** `species` только из допустимого enum; `goal=growth` допустим только если `age_months < 18`
- **Безопасность:** `telegram_id` берётся только из Telegram webhook, не из тела запроса
- **Интеграционные:** проверка уникальности `telegram_id` перед созданием пользователя
- **Ограничения:** MVP — не более 1 питомца на пользователя

### 4. Основная логика

```
1. Получить telegram_id из webhook-события Telegram
2. SELECT * FROM users WHERE telegram_id = :telegram_id
3. Если пользователь НЕ существует:
     INSERT INTO users (telegram_id, username) VALUES (...)
4. Если пользователь существует и has_pet = true:
     → вернуть главное меню (пропустить онбординг)
5. Валидировать все поля профиля питомца
6. INSERT INTO pets (owner_id, name, species, breed, age_months, weight_kg, goal)
7. INSERT INTO weight_history (pet_id, weight_kg, recorded_at = TODAY)
8. Вернуть созданный профиль питомца
```

### 5. Интеграции

- **PostgreSQL:** чтение/запись таблиц `users`, `pets`, `weight_history`
- **Redis:** сохранение FSM-состояния диалога по ключу `fsm:{telegram_id}`
- **Telegram Bot API:** получение `telegram_id` и `username` из объекта `message.from`

### 6. Исключительные ситуации

| Ошибка | HTTP | Описание |
|---|---|---|
| Невалидный species | 400 | `{"error": "invalid_species", "allowed": ["cat","dog","rodent","bird","reptile"]}` |
| Невалидный weight_kg | 400 | `{"error": "invalid_weight", "message": "Вес должен быть больше 0"}` |
| Невалидный age_months | 400 | `{"error": "invalid_age", "message": "Возраст не может быть отрицательным"}` |
| goal=growth, age >= 18 мес | 400 | `{"error": "invalid_goal", "message": "Цель роста доступна только для молодых животных"}` |
| Ошибка сохранения | 500 | `{"error": "internal_error", "message": "Попробуйте позже"}` |

### 7. Выходные данные

```json
{
  "user": {
    "id": 1,
    "telegram_id": 123456789
  },
  "pet": {
    "id": 1,
    "name": "Барсик",
    "species": "cat",
    "breed": "Мейн-кун",
    "age_months": 24,
    "weight_kg": 5.20,
    "goal": "maintain"
  }
}
```

### 8. Производительность
- Создание профиля: не более 500 мс
- FSM-состояние в Redis TTL: 30 минут

---

## BL-002: Расчёт персонального рациона питания

### 1. Общий обзор
Система рассчитывает суточную норму калорий и порции на основе параметров питомца и его цели. Использует базу знаний `nutrition_knowledge`. Связан с UC-002, US-004, US-006.

### 2. Входные данные

| Параметр | Тип | Ограничения |
|---|---|---|
| `pet_id` | int | Обязательный, должен принадлежать текущему пользователю |
| `goal` | string | Enum: maintain, lose, gain, growth |

### 3. Валидации

- **Безопасность:** `pet_id` проверяется на принадлежность `user_id` из сессии
- **Бизнес-правила:** при `weight_kg` за пределами нормы (±30% от среднего для вида) — добавить предупреждение
- **Интеграционные:** если база знаний не содержит данных для вида/породы — fallback на базовые нормы
- **Структурные:** `goal` только из допустимого enum

### 4. Основная логика

```
1. Загрузить питомца: SELECT * FROM pets WHERE id = :pet_id AND owner_id = :user_id
2. Рассчитать суточные калории по формуле RER:
     RER = 70 * (weight_kg ^ 0.75)
3. Применить коэффициент цели:
     maintain → RER * 1.0
     lose     → RER * 0.8
     gain     → RER * 1.2
     growth   → RER * 1.5  (если age_months < 12)
               RER * 1.2  (если age_months 12–18)
4. Рассчитать частоту кормлений по возрасту и виду:
     Котята/щенки (< 6 мес)  → 4 раза в день
     Молодые (6–12 мес)       → 3 раза в день
     Взрослые (> 12 мес)      → 2 раза в день
     Грызуны/птицы            → постоянный доступ к сухому корму
     Рептилии                 → 1 раз в 1–3 дня (фиксируем как 1/день)
5. Рассчитать размер порции:
     portion_grams = (daily_calories / feedings_per_day) / 4  (ккал/г ≈ 4 для сухого корма)
6. Получить список разрешённых продуктов:
     SELECT product_name FROM nutrition_knowledge
     WHERE species = :species AND is_allowed = TRUE
7. Получить стоп-лист:
     SELECT product_name, danger_level, reason FROM nutrition_knowledge
     WHERE species = :species AND is_allowed = FALSE
8. Проверить критический вес:
     Если weight_kg > norm_max[species] * 1.3 → флаг weight_warning = true
9. Сохранить или обновить рацион:
     INSERT INTO rations (...) ON CONFLICT (pet_id) DO UPDATE SET ...
10. Вернуть рацион с разрешёнными и запрещёнными продуктами
```

### 5. Интеграции

- **PostgreSQL:** чтение `pets`, `nutrition_knowledge`; запись `rations`
- **Redis:** кэш рациона по ключу `ration:{pet_id}` TTL 24 часа (инвалидируется при обновлении веса)

### 6. Исключительные ситуации

| Ошибка | HTTP | Описание |
|---|---|---|
| Питомец не найден / чужой | 404 | `{"error": "pet_not_found"}` |
| Нет данных в базе знаний | 200 | Возвращается с флагом `data_source: "basic"` и пометкой |
| Критический вес | 200 | Возвращается с флагом `weight_warning: true` |
| Ошибка расчёта | 500 | `{"error": "calculation_error"}` |

### 7. Выходные данные

```json
{
  "ration": {
    "daily_calories": 280,
    "portion_grams": 35,
    "feedings_per_day": 2,
    "goal": "maintain"
  },
  "allowed_foods": ["Куриная грудка варёная", "Индейка", "Рис"],
  "stop_list": [
    {"product": "Лук", "danger_level": "dangerous", "reason": "Вызывает анемию"},
    {"product": "Шоколад", "danger_level": "fatal", "reason": "Теобромин токсичен"}
  ],
  "weight_warning": false,
  "data_source": "knowledge_base"
}
```

### 8. Производительность
- Расчёт рациона: не более 300 мс
- Кэш рациона в Redis: TTL 24 часа

---

## BL-003: Управление напоминаниями о кормлении

### 1. Общий обзор
Пользователь настраивает расписание кормлений. Планировщик (APScheduler) отправляет уведомления через Telegram Bot API в указанное время. Связан с UC-003, US-008.

### 2. Входные данные

| Параметр | Тип | Ограничения |
|---|---|---|
| `pet_id` | int | Обязательный, принадлежит пользователю |
| `reminder_times` | array[time] | Обязательный, 1–6 элементов, формат HH:MM |
| `timezone` | string | Обязательный, IANA timezone (Europe/Moscow) |

### 3. Валидации

- **Структурные:** каждое время в формате HH:MM; длина массива 1–6
- **Бизнес-правила:** не более 6 напоминаний на питомца в сутки (AC-004)
- **Безопасность:** `pet_id` принадлежит текущему пользователю
- **Интеграционные:** таймзона из списка допустимых IANA timezone
- **Ограничения:** при деактивации — все напоминания питомца помечаются `is_active = FALSE`

### 4. Основная логика

```
1. Валидировать pet_id принадлежит user_id
2. Валидировать список времён: COUNT <= 6, формат HH:MM
3. Валидировать timezone через pytz.all_timezones
4. Удалить старые напоминания питомца:
     DELETE FROM feeding_reminders WHERE pet_id = :pet_id
5. Создать новые напоминания:
     INSERT INTO feeding_reminders (pet_id, reminder_time, timezone)
     VALUES (:pet_id, :time, :timezone) FOR EACH time
6. APScheduler: зарегистрировать cron-задачи для каждого напоминания:
     scheduler.add_job(send_reminder, 'cron',
         hour=HH, minute=MM,
         timezone=timezone,
         args=[telegram_id, pet_id, reminder_id])
7. Вернуть список созданных напоминаний
```

### 5. Интеграции

- **PostgreSQL:** удаление и запись `feeding_reminders`
- **APScheduler:** регистрация cron-задач в памяти
- **Telegram Bot API:** отправка push-уведомления через `bot.send_message()`

### 6. Исключительные ситуации

| Ошибка | HTTP | Описание |
|---|---|---|
| Питомец не найден | 404 | `{"error": "pet_not_found"}` |
| Более 6 напоминаний | 400 | `{"error": "too_many_reminders", "max": 6}` |
| Неверный формат времени | 400 | `{"error": "invalid_time_format", "expected": "HH:MM"}` |
| Неверная таймзона | 400 | `{"error": "invalid_timezone"}` |
| Telegram недоступен | 503 | Задача помечается, повтор через 5 минут |

### 7. Выходные данные

```json
{
  "reminders": [
    {"id": 1, "time": "08:00", "timezone": "Europe/Moscow", "is_active": true},
    {"id": 2, "time": "18:00", "timezone": "Europe/Moscow", "is_active": true}
  ],
  "pet_id": 1
}
```

### 8. Производительность
- Сохранение расписания: не более 300 мс
- Точность отправки напоминания: ±1 минута (AC-004)

---

## BL-004: Заказ корма через партнёра

### 1. Общий обзор
Система формирует уникальную реферальную ссылку и фиксирует переход пользователя к партнёру. При получении webhook от партнёра — подтверждает заказ и начисляет комиссию. Связан с UC-004, US-011.

### 2. Входные данные

**Создание перехода:**

| Параметр | Тип | Ограничения |
|---|---|---|
| `pet_id` | int | Обязательный |
| `product_id` | int | Обязательный, товар должен быть `is_available = TRUE` |

**Webhook от партнёра:**

| Параметр | Тип | Ограничения |
|---|---|---|
| `referral_token` | string | Обязательный, уникальный |
| `partner_api_key` | string | Обязательный, для аутентификации |

### 3. Валидации

- **Безопасность:** webhook аутентифицируется по `partner_api_key` (сравнение с хэшем в БД)
- **Бизнес-правила:** товар должен быть доступен у партнёра (`is_available = TRUE`)
- **Интеграционные:** `referral_token` должен существовать в таблице `orders` со статусом `pending`
- **Ограничения:** повторная обработка одного `referral_token` — идемпотентность

### 4. Основная логика

```
Создание реферальной ссылки:
1. Проверить product_id: SELECT * FROM products WHERE id = :product_id AND is_available = TRUE
2. Получить партнёра: SELECT * FROM partners WHERE id = :partner_id AND is_active = TRUE
3. Сгенерировать уникальный токен: referral_token = uuid4()
4. Записать заказ:
     INSERT INTO orders (user_id, pet_id, product_id, partner_id, referral_token, status='pending')
5. Сформировать реферальную ссылку:
     url = f"{partner.website_url}/product/{product.external_id}?ref={referral_token}"
6. Вернуть ссылку пользователю

Обработка webhook от партнёра:
1. Извлечь X-Api-Key из заголовка запроса
2. SELECT * FROM partners WHERE api_key_hash = hash(X-Api-Key)
3. Если партнёр не найден → 401 Unauthorized
4. Найти заказ: SELECT * FROM orders WHERE referral_token = :token AND status = 'pending'
5. Если не найден → 404; если уже confirmed → 200 (идемпотентность)
6. Рассчитать комиссию:
     commission = product.price * (partner.commission_pct / 100)
7. UPDATE orders SET status='confirmed', commission_amount=:commission, confirmed_at=NOW()
8. Вернуть 200 OK
```

### 5. Интеграции

- **PostgreSQL:** чтение `products`, `partners`; запись и обновление `orders`
- **Telegram Bot API:** уведомление пользователя об успешном заказе (после webhook)

### 6. Исключительные ситуации

| Ошибка | HTTP | Описание |
|---|---|---|
| Товар недоступен | 404 | `{"error": "product_unavailable"}` |
| Партнёр недоступен | 503 | `{"error": "partner_unavailable"}` |
| Неверный API ключ партнёра | 401 | `{"error": "unauthorized"}` |
| Токен не найден | 404 | `{"error": "token_not_found"}` |
| Заказ уже подтверждён | 200 | Идемпотентный ответ |

### 7. Выходные данные

```json
{
  "order_id": 42,
  "referral_token": "550e8400-e29b-41d4-a716-446655440000",
  "redirect_url": "https://zooshop.example.com/product/cat-food-123?ref=550e8400...",
  "product": {
    "name": "Royal Canin Maine Coon",
    "price": 1890.00,
    "partner": "ZooShop"
  }
}
```

### 8. Производительность
- Формирование ссылки: не более 200 мс
- Обработка webhook: не более 500 мс
- Таймаут ожидания webhook: 24 часа, затем статус `pending` остаётся

---

## BL-005: AI-ассистент по питанию

### 1. Общий обзор
Принимает вопрос пользователя, обогащает его контекстом профиля питомца и отправляет запрос в DeepSeek API. Кэширует ответы в Redis. Ведёт счётчик суточных запросов. Связан с UC-007, US-014.

### 2. Входные данные

| Параметр | Тип | Ограничения |
|---|---|---|
| `pet_id` | int | Обязательный |
| `question` | string | Обязательный, 5–1000 символов |

### 3. Валидации

- **Структурные:** длина вопроса 5–1000 символов
- **Бизнес-правила:** не более 10 запросов в день для бесплатного пользователя (AC-007)
- **Безопасность:** `pet_id` принадлежит текущему пользователю
- **Интеграционные:** при недоступности DeepSeek API — поиск в кэше Redis
- **Ограничения:** вопрос должен касаться питания животных (базовая фильтрация по ключевым словам)

### 4. Основная логика

```
1. Проверить лимит запросов пользователя:
     SELECT ai_requests_today, ai_requests_reset_at FROM users WHERE id = :user_id
     Если reset_at < NOW() - 24h → обнулить счётчик
     Если ai_requests_today >= 10 → вернуть 429 Too Many Requests
2. Загрузить профиль питомца:
     SELECT species, breed, age_months, weight_kg, goal FROM pets WHERE id = :pet_id
3. Проверить кэш Redis:
     cache_key = md5(f"{species}:{breed}:{question}")
     cached = redis.get(cache_key)
     Если кэш найден → вернуть cached_answer, is_cached=True
4. Сформировать промпт для DeepSeek:
     system_prompt = "Ты эксперт по питанию домашних животных..."
     user_context = f"Питомец: {species}, порода {breed}, возраст {age_months} мес, вес {weight_kg} кг"
     full_prompt = f"{user_context}\n\nВопрос: {question}"
5. Отправить запрос в DeepSeek API:
     response = deepseek_client.chat.completions.create(
         model="deepseek-chat",
         messages=[
             {"role": "system", "content": system_prompt},
             {"role": "user", "content": full_prompt}
         ]
     )
6. Сохранить ответ в Redis:
     redis.setex(cache_key, 86400, answer)   # TTL 24 часа
7. Сохранить в БД:
     INSERT INTO ai_requests (user_id, pet_id, question, answer, is_cached)
8. Увеличить счётчик:
     UPDATE users SET ai_requests_today = ai_requests_today + 1
9. Вернуть ответ с дисклеймером
```

### 5. Интеграции

- **PostgreSQL:** чтение `users`, `pets`; запись `ai_requests`; обновление счётчика `users.ai_requests_today`
- **Redis:** кэш ответов по ключу `ai:{md5(species:breed:question)}`; TTL 24 часа
- **DeepSeek API:** `POST /v1/chat/completions`, модель `deepseek-chat`

### 6. Исключительные ситуации

| Ошибка | HTTP | Описание |
|---|---|---|
| Лимит запросов исчерпан | 429 | `{"error": "rate_limit", "reset_at": "2026-04-19T00:00:00"}` |
| Вопрос слишком короткий | 400 | `{"error": "question_too_short", "min_length": 5}` |
| DeepSeek API недоступен | 503 | Fallback на кэш; если кэша нет — `{"error": "ai_unavailable"}` |
| Питомец не найден | 404 | `{"error": "pet_not_found"}` |

### 7. Выходные данные

```json
{
  "answer": "Мейн-кунам в возрасте 2 лет рекомендуется кормить 2 раза в день...",
  "is_cached": false,
  "disclaimer": "Ответ носит информационный характер и не заменяет консультацию ветеринара.",
  "requests_remaining": 7
}
```

### 8. Производительность
- Ответ из кэша: не более 100 мс
- Ответ от DeepSeek API: не более 10 секунд (AC-007)
- Таймаут запроса к DeepSeek: 15 секунд

---

## BL-006: Обновление веса и пересчёт рациона

### 1. Общий обзор
Пользователь вносит новый вес питомца. Система сохраняет запись, вычисляет динамику и при отклонении ≥5% пересчитывает рацион. Связан с UC-006, US-010, AC-006.

### 2. Входные данные

| Параметр | Тип | Ограничения |
|---|---|---|
| `pet_id` | int | Обязательный |
| `weight_kg` | decimal | Обязательный, > 0 |

### 3. Валидации

- **Структурные:** `weight_kg` > 0, decimal(5,2)
- **Бизнес-правила:** не более одной записи веса в день (AC-006, UNIQUE constraint)
- **Безопасность:** `pet_id` принадлежит текущему пользователю
- **Ограничения:** вес за физиологической нормой вида → предупреждение

### 4. Основная логика

```
1. Проверить pet_id принадлежит user_id
2. Проверить существование записи за сегодня:
     SELECT id FROM weight_history WHERE pet_id = :pet_id AND recorded_at = TODAY
     Если существует → 409 Conflict
3. Получить предыдущий вес:
     SELECT weight_kg FROM weight_history
     WHERE pet_id = :pet_id ORDER BY recorded_at DESC LIMIT 1
4. Вычислить изменение:
     delta_pct = ((new_weight - prev_weight) / prev_weight) * 100
5. Записать новый вес:
     INSERT INTO weight_history (pet_id, weight_kg, recorded_at = TODAY)
6. Обновить вес в профиле питомца:
     UPDATE pets SET weight_kg = :new_weight, updated_at = NOW()
7. Если |delta_pct| >= 5%:
     → вызвать BL-002 (пересчёт рациона)
     → инвалидировать кэш Redis: redis.delete(f"ration:{pet_id}")
     → флаг ration_updated = true
8. Если |delta_pct| >= 10%:
     → флаг critical_change = true
     → добавить рекомендацию обратиться к ветеринару
9. Вернуть новый вес, динамику и флаги
```

### 5. Интеграции

- **PostgreSQL:** запись `weight_history`, обновление `pets`, чтение предыдущего веса
- **Redis:** инвалидация кэша `ration:{pet_id}` при изменении ≥5%

### 6. Исключительные ситуации

| Ошибка | HTTP | Описание |
|---|---|---|
| Питомец не найден | 404 | `{"error": "pet_not_found"}` |
| Запись за сегодня уже есть | 409 | `{"error": "already_recorded_today"}` |
| Некорректный вес | 400 | `{"error": "invalid_weight"}` |

### 7. Выходные данные

```json
{
  "weight_kg": 5.40,
  "prev_weight_kg": 5.20,
  "delta_pct": 3.8,
  "ration_updated": false,
  "critical_change": false,
  "recorded_at": "2026-04-18"
}
```

### 8. Производительность
- Запись веса и пересчёт: не более 500 мс

---

## Сводная таблица связности

| Модуль | US | UC | AC | Таблицы БД | Внешние интеграции |
|---|---|---|---|---|---|
| BL-001 Регистрация и профиль | US-001, 003 | UC-001 | AC-001 | users, pets, weight_history | Telegram Bot API, Redis FSM |
| BL-002 Расчёт рациона | US-004, 006, 007 | UC-002 | AC-002 | pets, rations, nutrition_knowledge | Redis кэш |
| BL-003 Напоминания | US-008 | UC-003 | AC-004 | feeding_reminders | APScheduler, Telegram Bot API |
| BL-004 Заказ корма | US-011 | UC-004 | AC-005 | orders, products, partners | Telegram Bot API |
| BL-005 AI-ассистент | US-014 | UC-007 | AC-007 | ai_requests, users | DeepSeek API, Redis кэш |
| BL-006 Обновление веса | US-010 | UC-006 | AC-006 | weight_history, pets, rations | Redis инвалидация |

---

*Документ создан: 2026-04-18*
*Связанные артефакты: petfeed_erd.plantuml, use_cases_uc.md, acceptance_criteria_ac.md*
