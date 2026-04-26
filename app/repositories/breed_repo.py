from rapidfuzz import process, fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.breed_registry import BreedRegistry


class BreedRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, species: str) -> list[BreedRegistry]:
        result = await self.session.execute(
            select(BreedRegistry).where(BreedRegistry.species == species)
        )
        return list(result.scalars().all())

    async def get_by_id(self, breed_id: int) -> BreedRegistry | None:
        return await self.session.get(BreedRegistry, breed_id)

    async def fuzzy_search(self, query: str, species: str) -> list[tuple[BreedRegistry, float]]:
        breeds = await self.get_all(species)
        if not breeds:
            return []

        corpus: dict[str, int] = {}
        for breed in breeds:
            corpus[breed.canonical_name.lower()] = breed.id
            corpus[breed.canonical_name_ru.lower()] = breed.id
            for alias in (breed.aliases or []):
                corpus[alias.lower()] = breed.id

        results = process.extract(
            query.lower(), list(corpus.keys()), scorer=fuzz.WRatio, limit=10
        )

        best_per_breed: dict[int, float] = {}
        for match_str, score, _ in results:
            breed_id = corpus[match_str]
            if breed_id not in best_per_breed or score > best_per_breed[breed_id]:
                best_per_breed[breed_id] = score

        top = sorted(best_per_breed.items(), key=lambda x: x[1], reverse=True)[:3]
        id_to_breed = {b.id: b for b in breeds}
        return [(id_to_breed[bid], score) for bid, score in top if bid in id_to_breed]
