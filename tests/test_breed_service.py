import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.breed_service import BreedService, MatchConfidence
from app.models.breed_registry import BreedRegistry


def make_breed(id, canonical_name, canonical_name_ru, species="dog", aliases=None):
    b = BreedRegistry()
    b.id = id
    b.canonical_name = canonical_name
    b.canonical_name_ru = canonical_name_ru
    b.species = species
    b.aliases = aliases or []
    return b


@pytest.fixture
def jrt():
    return make_breed(1, "Jack Russell Terrier", "Джек Рассел Терьер",
                      aliases=["JRT", "джек расел", "jack russel"])


@pytest.fixture
def labrador():
    return make_breed(2, "Labrador Retriever", "Лабрадор Ретривер",
                      aliases=["лабрадор", "labrador"])


@pytest.mark.asyncio
async def test_high_confidence_exact_match(jrt, labrador):
    repo = MagicMock()
    repo.fuzzy_search = AsyncMock(return_value=[(jrt, 100.0), (labrador, 30.0)])
    result = await BreedService(repo).match_text("Jack Russell Terrier", "dog")
    assert result.confidence == MatchConfidence.HIGH
    assert result.candidates[0].canonical_name == "Jack Russell Terrier"


@pytest.mark.asyncio
async def test_medium_confidence_typo(jrt, labrador):
    repo = MagicMock()
    repo.fuzzy_search = AsyncMock(return_value=[(jrt, 75.0), (labrador, 45.0)])
    result = await BreedService(repo).match_text("джек расел", "dog")
    assert result.confidence == MatchConfidence.MEDIUM
    assert len(result.candidates) >= 1
    assert result.candidates[0].canonical_name == "Jack Russell Terrier"


@pytest.mark.asyncio
async def test_low_confidence_no_matches():
    repo = MagicMock()
    repo.fuzzy_search = AsyncMock(return_value=[])
    result = await BreedService(repo).match_text("абракадабра", "dog")
    assert result.confidence == MatchConfidence.LOW
    assert result.candidates == []


@pytest.mark.asyncio
async def test_low_confidence_poor_score(jrt):
    repo = MagicMock()
    repo.fuzzy_search = AsyncMock(return_value=[(jrt, 45.0)])
    result = await BreedService(repo).match_text("zzzzzzz", "dog")
    assert result.confidence == MatchConfidence.LOW


@pytest.mark.asyncio
async def test_raw_input_preserved(jrt):
    repo = MagicMock()
    repo.fuzzy_search = AsyncMock(return_value=[(jrt, 75.0)])
    result = await BreedService(repo).match_text("джек расел", "dog")
    assert result.raw_input == "джек расел"


@pytest.mark.asyncio
async def test_top_candidates_capped_at_3(jrt, labrador):
    extra = make_breed(3, "Beagle", "Бигль")
    repo = MagicMock()
    repo.fuzzy_search = AsyncMock(return_value=[
        (jrt, 80.0), (labrador, 72.0), (extra, 65.0)
    ])
    result = await BreedService(repo).match_text("query", "dog")
    assert len(result.candidates) <= 3


@pytest.mark.asyncio
async def test_high_threshold_boundary(jrt):
    repo = MagicMock()
    repo.fuzzy_search = AsyncMock(return_value=[(jrt, 85.0)])
    result = await BreedService(repo).match_text("jack", "dog")
    assert result.confidence == MatchConfidence.HIGH


@pytest.mark.asyncio
async def test_medium_threshold_boundary(jrt):
    repo = MagicMock()
    repo.fuzzy_search = AsyncMock(return_value=[(jrt, 60.0)])
    result = await BreedService(repo).match_text("jack", "dog")
    assert result.confidence == MatchConfidence.MEDIUM
