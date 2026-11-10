from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..services import gemini_service
from ..services.analytics_service import compute_analytics
from ..services.order_service import load_unified_orders

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return compute_analytics(load_unified_orders(db, user.id))


@router.post("/insights")
def insights(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    data = compute_analytics(load_unified_orders(db, user.id))
    if not data["by_currency"]:
        return {"insights": [], "message": "Add or import some orders first - there is nothing to analyse yet."}
    try:
        return {"insights": gemini_service.narrate_insights({"by_currency": data["by_currency"]})}
    except gemini_service.GeminiError as e:
        raise HTTPException(e.status_code, str(e))
