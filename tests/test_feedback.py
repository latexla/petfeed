import pytest
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
