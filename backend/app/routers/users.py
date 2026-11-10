from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User, UserPreference
from ..schemas import PreferenceIn, UserOut, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(body: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.full_name is not None:
        user.full_name = body.full_name.strip()
    if body.preferred_language is not None:
        user.preferred_language = body.preferred_language
    db.commit()
    return user


@router.get("/me/preferences")
def list_preferences(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(UserPreference).where(UserPreference.user_id == user.id).order_by(UserPreference.key)).all()
    return [{"key": r.key, "value": r.value, "updated_at": r.updated_at.isoformat()} for r in rows]


@router.put("/me/preferences")
def set_preference(body: PreferenceIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(UserPreference).where(UserPreference.user_id == user.id, UserPreference.key == body.key))
    if row:
        row.value = body.value
    else:
        db.add(UserPreference(user_id=user.id, key=body.key, value=body.value))
    db.commit()
    return {"key": body.key, "value": body.value}


@router.delete("/me/preferences/{key}", status_code=204)
def delete_preference(key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(UserPreference).where(UserPreference.user_id == user.id, UserPreference.key == key))
    if not row:
        raise HTTPException(404, "Preference not found")
    db.delete(row)
    db.commit()
