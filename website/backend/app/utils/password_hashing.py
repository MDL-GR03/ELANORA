"""One password hashing context for the whole application."""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    hashed: str = pwd_context.hash(password)
    return hashed


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Whether a plain password matches a stored bcrypt hash."""
    return bool(pwd_context.verify(plain_password, hashed_password))
