from app.models.user_feedback import UserFeedback


def test_user_feedback_model():
    fb = UserFeedback(user_id=1, rating=5, top_feature="Рацион питания", source="manual")
    assert fb.user_id == 1
    assert fb.rating == 5
    assert fb.top_feature == "Рацион питания"
    assert fb.comment is None
    assert fb.source == "manual"
