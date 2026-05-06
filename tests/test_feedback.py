import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.user_feedback import UserFeedback


def test_user_feedback_model():
    fb = UserFeedback(user_id=1, rating=5, top_feature="Рацион питания", source="manual")
    assert fb.user_id == 1
    assert fb.rating == 5
    assert fb.top_feature == "Рацион питания"
    assert fb.comment is None
    assert fb.source == "manual"


class TestFeedbackCreate:
    def test_valid_payload(self):
        from app.routers.feedback import FeedbackCreate
        fb = FeedbackCreate(rating=5, top_feature="Напоминания", comment="Отлично!", source="auto_7d")
        assert fb.rating == 5
        assert fb.source == "auto_7d"
        assert fb.comment == "Отлично!"

    def test_rating_too_high_rejected(self):
        from pydantic import ValidationError
        from app.routers.feedback import FeedbackCreate
        with pytest.raises(ValidationError):
            FeedbackCreate(rating=6, top_feature="Рацион питания")

    def test_rating_too_low_rejected(self):
        from pydantic import ValidationError
        from app.routers.feedback import FeedbackCreate
        with pytest.raises(ValidationError):
            FeedbackCreate(rating=0, top_feature="Рацион питания")

    def test_defaults(self):
        from app.routers.feedback import FeedbackCreate
        fb = FeedbackCreate(rating=3, top_feature="AI-ассистент")
        assert fb.source == "manual"
        assert fb.comment is None


@pytest.mark.asyncio
@pytest.mark.skip(reason="requires real DB")
class TestFeedbackEndpoint:
    async def test_submit_success(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/v1/feedback",
                json={"rating": 5, "top_feature": "Рацион питания"},
                headers={"X-Telegram-Id": "111222333"},
            )
        assert resp.status_code == 201
        assert resp.json()["status"] == "ok"

    async def test_submit_invalid_rating(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/v1/feedback",
                json={"rating": 10, "top_feature": "Рацион питания"},
                headers={"X-Telegram-Id": "111222444"},
            )
        assert resp.status_code == 422
