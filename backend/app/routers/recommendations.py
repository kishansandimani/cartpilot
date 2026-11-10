from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import AIRecommendation, Product, User
from ..schemas import ExplainIn
from ..services import gemini_service
from ..services.product_service import product_to_dict

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("")
def recent(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(AIRecommendation).where(AIRecommendation.user_id == user.id)
                      .order_by(AIRecommendation.id.desc()).limit(20)).all()
    out = []
    for r in rows:
        p = db.get(Product, r.product_id)
        out.append({"id": r.id, "reason": r.reason, "pros": r.pros, "cons": r.cons, "product": product_to_dict(p),
                    "created_at": r.created_at.isoformat()})
    return out


@router.post("/explain")
def explain(body: ExplainIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(Product, body.product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    rec = db.scalar(select(AIRecommendation).where(AIRecommendation.user_id == user.id, AIRecommendation.product_id == p.id)
                    .order_by(AIRecommendation.id.desc()))
    if rec is None:
        raise HTTPException(404, "I haven't recommended this product to you yet.")
    try:
        text = gemini_service.explain_recommendation("", product_to_dict(p), rec.reason)
    except gemini_service.GeminiError:
        text = rec.reason or ""  # fall back to the explanation saved earlier
    return {"explanation": text}
