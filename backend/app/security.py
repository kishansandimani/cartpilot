import bcrypt
import jwt
from datetime import datetime, timedelta, timezone

from .config import get_settings


def hash_password(password: str) -> str:
    # bcrypt only reads the first 72 bytes; we reject longer passwords at the schema level.
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=s.access_token_minutes)
    return jwt.encode({"sub": str(user_id), "exp": exp}, s.require_jwt_secret(), algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.require_jwt_secret(), algorithms=[s.jwt_algorithm])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
