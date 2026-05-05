"""seed_feature_flags

Revision ID: d1e2f3a4b5c6
Revises: a1b2c3
Create Date: 2026-05-05 00:00:00.000000

Seed all feature flags with default values.
feature_orders and feature_subscription are OFF — monetization is disabled for MVP phase.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'a1b2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FLAGS = [
    ("feature_pet_profile",     "Профиль питомца",              "Создание и редактирование профиля",                          True),
    ("feature_nutrition",       "Рекомендации по питанию",      "Расчёт рациона и стоп-лист",                                 True),
    ("feature_reminders",       "Напоминания о кормлении",      "Push-уведомления через Telegram",                            True),
    ("feature_feeding_log",     "Журнал кормлений",             "Ведение дневника кормлений",                                 True),
    ("feature_weight_tracking", "Трекер веса",                  "Внесение веса и динамика",                                   True),
    ("feature_ai_assistant",    "AI-ассистент",                 "Вопросы через DeepSeek API",                                 True),
    ("feature_multi_pet",       "Несколько питомцев",           "Более 1 питомца на аккаунт",                                 True),
    ("feature_admin_panel",     "Admin Panel",                  "Веб-интерфейс администратора",                               True),
    ("feature_partner_catalog", "Каталог партнёров",            "Показ товаров нескольких партнёров",                         True),
    # Monetization — disabled until partner integrations are ready
    ("feature_orders",          "Заказ корма",                  "Переходы к партнёрам и реферальные ссылки",                  False),
    ("feature_partner_webhook", "Webhook партнёров",            "Приём уведомлений о заказах от партнёров",                   False),
    ("feature_subscription",    "Подписка Premium",             "Платная подписка и снятие лимитов",                          False),
    # Phase 2
    ("feature_food_scanner",    "Сканер корма",                 "Анализ состава корма по фото/названию",                      False),
    ("feature_vet_referral",    "Реферал ветклиники",           "Раздел «Рекомендовано ветеринаром»",                         False),
]


def upgrade() -> None:
    for key, name, description, is_enabled in FLAGS:
        op.execute(
            f"""
            INSERT INTO feature_flags (key, name, description, is_enabled, updated_by)
            VALUES (
                '{key}',
                '{name}',
                '{description}',
                {'true' if is_enabled else 'false'},
                'migration'
            )
            ON CONFLICT (key) DO UPDATE
                SET is_enabled  = EXCLUDED.is_enabled,
                    name        = EXCLUDED.name,
                    description = EXCLUDED.description,
                    updated_by  = 'migration',
                    updated_at  = now()
            """
        )


def downgrade() -> None:
    pass
