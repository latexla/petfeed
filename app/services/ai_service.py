import hashlib
import json
import logging
from datetime import date
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models.user import User
from app.models.pet import Pet
from app.models.ai_request import AiRequest
from app.redis_client import get_redis

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты — AI-нутрициолог для домашних животных в сервисе PetFeed. "
    "Отвечай только на вопросы о питании, здоровье и уходе за питомцами. "
    "Давай конкретные, безопасные советы. Если вопрос требует ветеринара — скажи об этом. "
    "Отвечай на русском языке, кратко и по делу (не более 200 слов)."
)


class AiService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        )

    def _cache_key(self, question: str, species: str) -> str:
        h = hashlib.md5(f"{species}:{question.lower().strip()}".encode()).hexdigest()
        return f"ai_cache:{h}"

    def _limit_key(self, user_id: int) -> str:
        today = date.today().isoformat()
        return f"ai_limit:{user_id}:{today}"

    async def check_limit(self, user: User) -> tuple[bool, int]:
        """Returns (can_ask, requests_left)"""
        redis = get_redis()
        key = self._limit_key(user.id)
        count = await redis.get(key)
        used = int(count) if count else 0
        remaining = settings.AI_DAILY_LIMIT - used
        return remaining > 0, remaining

    async def ask(self, user: User, pet: Pet | None, question: str) -> tuple[str, bool]:
        """Returns (answer, cache_hit)"""
        species = pet.species if pet else "unknown"
        redis = get_redis()
        cache_key = self._cache_key(question, species)

        cached = await redis.get(cache_key)
        if cached:
            return cached, True

        limit_key = self._limit_key(user.id)
        count = await redis.get(limit_key)
        used = int(count) if count else 0
        if used >= settings.AI_DAILY_LIMIT:
            return f"Лимит исчерпан ({settings.AI_DAILY_LIMIT} запросов/день). Завтра доступно снова.", False

        context = ""
        if pet:
            context = (
                f"Питомец: {pet.name}, вид: {pet.species}, "
                f"возраст: {pet.age_months} мес, вес: {pet.weight_kg} кг. "
            )

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"{context}Вопрос: {question}"}
                ],
                max_tokens=400,
                temperature=0.7
            )
            answer = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            return "Сервис временно недоступен. Попробуй позже.", False

        await redis.set(cache_key, answer, ex=86400)
        await redis.set(limit_key, used + 1, ex=86400)

        record = AiRequest(
            user_id=user.id,
            pet_id=pet.id if pet else None,
            question=question,
            answer=answer,
            cache_hit=False
        )
        self.session.add(record)
        await self.session.commit()

        return answer, False
