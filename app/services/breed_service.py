import base64
import logging
from dataclasses import dataclass
from enum import Enum

from openai import AsyncOpenAI
from app.config import settings
from app.repositories.breed_repo import BreedRepository

logger = logging.getLogger(__name__)

HIGH_THRESHOLD = 85
MEDIUM_THRESHOLD = 60


class MatchConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class BreedCandidate:
    breed_id: int
    canonical_name: str
    canonical_name_ru: str
    score: float


@dataclass
class BreedMatchResult:
    confidence: MatchConfidence
    candidates: list[BreedCandidate]
    raw_input: str


class BreedService:
    def __init__(self, repo: BreedRepository):
        self.repo = repo

    async def match_text(self, text: str, species: str) -> BreedMatchResult:
        matches = await self.repo.fuzzy_search(text, species)
        return self._build_result(matches, text)

    def _build_result(self, matches: list, raw_input: str) -> BreedMatchResult:
        if not matches:
            return BreedMatchResult(
                confidence=MatchConfidence.LOW,
                candidates=[],
                raw_input=raw_input,
            )
        top_score = matches[0][1]
        if top_score >= HIGH_THRESHOLD:
            confidence = MatchConfidence.HIGH
        elif top_score >= MEDIUM_THRESHOLD:
            confidence = MatchConfidence.MEDIUM
        else:
            confidence = MatchConfidence.LOW

        candidates = [
            BreedCandidate(
                breed_id=b.id,
                canonical_name=b.canonical_name,
                canonical_name_ru=b.canonical_name_ru,
                score=s,
            )
            for b, s in matches
        ]
        return BreedMatchResult(
            confidence=confidence, candidates=candidates, raw_input=raw_input
        )

    async def recognize_from_photo(self, photo_bytes: bytes, species: str) -> BreedMatchResult:
        species_word = "dog" if species == "dog" else "cat"
        b64 = base64.b64encode(photo_bytes).decode()
        client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )
        try:
            response = await client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                            },
                            {
                                "type": "text",
                                "text": (
                                    f"What breed is this {species_word}? "
                                    "Reply with ONLY the breed name in English, nothing else."
                                ),
                            },
                        ],
                    }
                ],
                max_tokens=50,
            )
            breed_name = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Groq Vision error: {e}")
            return BreedMatchResult(
                confidence=MatchConfidence.LOW, candidates=[], raw_input=""
            )
        return await self.match_text(breed_name, species)
