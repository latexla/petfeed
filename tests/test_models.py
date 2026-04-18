from app.models.user import User
from app.models.pet import Pet
from app.models.feature_flag import FeatureFlag


def test_user_model_has_required_fields():
    u = User(telegram_id=123, username="test")
    assert u.telegram_id == 123
    assert u.username == "test"


def test_pet_model_has_required_fields():
    p = Pet(owner_id=1, name="Барсик", species="cat", age_months=24, weight_kg=5.2, goal="maintain")
    assert p.name == "Барсик"
    assert p.species == "cat"


def test_feature_flag_model():
    f = FeatureFlag(key="feature_nutrition", name="Питание", is_enabled=True)
    assert f.key == "feature_nutrition"
