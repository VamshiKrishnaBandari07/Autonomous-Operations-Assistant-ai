"""User service — authentication helpers and admin seeding."""

from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.core.security import hash_password, verify_password
from backend.models.user import User


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def ensure_admin_user(db: Session) -> User:
    """Create the default admin user if it does not exist."""
    settings = get_settings()
    user = get_user_by_username(db, settings.admin_username)
    if user:
        return user

    user = User(
        username=settings.admin_username,
        email=settings.admin_email,
        hashed_password=hash_password(settings.admin_password),
        full_name="OpsFlow Administrator",
        is_admin=True,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
