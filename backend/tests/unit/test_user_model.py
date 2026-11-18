"""Unit tests for User model schema."""

from app.db.models.user import User


def test_user_model_attributes():
    user = User(
        email="test@verdict.court",
        password_hash="argon2id$mockedhash",
        display_name="Advocate Aarav",
        is_guest=False,
    )

    assert user.email == "test@verdict.court"
    assert user.display_name == "Advocate Aarav"
    assert user.is_guest is False
    assert user.__tablename__ == "users"


def test_guest_user_instantiation():
    guest = User(
        display_name="Guest Juror",
        is_guest=True,
    )

    assert guest.email is None
    assert guest.password_hash is None
    assert guest.display_name == "Guest Juror"
    assert guest.is_guest is True
