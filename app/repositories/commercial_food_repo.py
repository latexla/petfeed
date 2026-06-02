from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commercial_food import CommercialFood


class CommercialFoodRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> list[CommercialFood]:
        result = await self.session.execute(select(CommercialFood))
        return list(result.scalars().all())

    async def get_by_id(self, food_id: int) -> CommercialFood | None:
        result = await self.session.execute(
            select(CommercialFood).where(CommercialFood.id == food_id)
        )
        return result.scalar_one_or_none()

    async def search(self, q: str, species: str, limit: int = 10) -> list[CommercialFood]:
        ql = q.lower()
        result = await self.session.execute(
            select(CommercialFood)
            .where(
                CommercialFood.species.in_([species, "all"]),
                or_(
                    func.lower(CommercialFood.name).contains(ql),
                    func.lower(CommercialFood.name_aliases).contains(ql),
                    func.lower(CommercialFood.brand).contains(ql),
                ),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def filter(
        self,
        species: str,
        food_type: str | None = None,
        life_stage: str | None = None,
        breed_size: str | None = None,
        tag: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[CommercialFood]:
        stmt = select(CommercialFood).where(
            CommercialFood.species.in_([species, "all"])
        )
        if food_type:
            stmt = stmt.where(CommercialFood.food_type == food_type)
        if life_stage:
            stmt = stmt.where(CommercialFood.life_stage.in_([life_stage, "all"]))
        if breed_size:
            stmt = stmt.where(
                or_(CommercialFood.breed_size == breed_size,
                    CommercialFood.breed_size == "all",
                    CommercialFood.breed_size.is_(None))
            )
        if tag:
            stmt = stmt.where(func.lower(CommercialFood.condition_tags).contains(tag.lower()))
        stmt = stmt.order_by(CommercialFood.brand, CommercialFood.name).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
