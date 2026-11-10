from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import AIRecommendation, ChatMessage, Conversation, ShoppingEvent, User, UserPreference
from ..schemas import ChatIn
from ..services import gemini_service
from ..services.product_provider import ProviderError, get_provider
from ..services.product_service import budget_for_provider, product_to_dict, upsert_product

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _save_pref(db: Session, user_id: int, key: str, value: str | None):
    if not value:
        return
    row = db.scalar(select(UserPreference).where(UserPreference.user_id == user_id, UserPreference.key == key))
    if row:
        row.value = value[:500]
    else:
        db.add(UserPreference(user_id=user_id, key=key, value=value[:500]))


def _over_budget(price_str: str, limit) -> bool:
    return limit is not None and Decimal(price_str) > Decimal(str(limit))


@router.post("")
def chat(body: ChatIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conv = None
    if body.conversation_id:
        conv = db.get(Conversation, body.conversation_id)
        if conv is None or conv.user_id != user.id:
            raise HTTPException(404, "Conversation not found")
    if conv is None:
        conv = Conversation(user_id=user.id, title=body.message[:60])
        db.add(conv)
        db.flush()
    history = [{"role": m.role, "content": m.content} for m in conv.messages]
    prefs = {p.key: p.value for p in db.scalars(select(UserPreference).where(UserPreference.user_id == user.id))}
    db.add(ChatMessage(conversation_id=conv.id, role="user", content=body.message))
    db.commit()  # release the database write lock BEFORE the slow Gemini call

    def finish(reply: str, products: list[dict] | None = None, **extra):
        db.add(ChatMessage(conversation_id=conv.id, role="assistant", content=reply,
                           meta={"product_ids": [p["id"] for p in products or []]}))
        db.commit()
        return {"conversation_id": conv.id, "reply": reply, "products": products or [], **extra}

    # ---- Step 1: understand the request (if Gemini is only busy, search with the user's words) ----
    ai_notes: list[str] = []
    try:
        req = gemini_service.extract_requirements(history, body.message, prefs)
    except gemini_service.GeminiError as e:
        if e.status_code != 503 or "not set" in str(e):
            db.rollback()
            raise HTTPException(e.status_code, str(e))
        req = {"needs_clarification": False, "clarifying_question": None, "search_query": body.message,
               "max_price": None, "min_price": None, "currency": None, "brand": None, "category": None,
               "must_have": [], "preferences": [], "wants_comparison": False}
        ai_notes.append("The AI is busy right now, so I searched using your words directly. "
                        "Budget and brand were not applied.")

    _save_pref(db, user.id, "preferred_brand", req["brand"])
    _save_pref(db, user.id, "last_category", req["category"])
    if req["max_price"] is not None:
        _save_pref(db, user.id, "last_budget", f"{req.get('currency') or ''} {req['max_price']}".strip())

    if req["needs_clarification"] or not req["search_query"]:
        return finish(req["clarifying_question"] or "What would you like to shop for? Tell me the product and your budget.",
                      needs_clarification=True, notes=[])

    # ---- Step 2: search real products ----
    max_price, min_price, note = budget_for_provider(req)
    try:
        provider = get_provider()
        found = provider.search(req["search_query"], max_price=max_price, min_price=min_price,
                                brand=req["brand"], limit=8)
    except ProviderError as e:
        db.rollback()
        raise HTTPException(502, str(e))
    notes = ([note] if note else []) + ai_notes
    if provider.name == "fixtures":
        notes.append("DEV MODE: these are clearly-labelled fixture products, not real listings.")
    if not found:
        return finish("I couldn't find matching products. Try relaxing the budget or describing the product differently.",
                      needs_clarification=False, notes=notes)

    products = [upsert_product(db, d) for d in found]
    db.commit()
    plist = [product_to_dict(p) for p in products]

    # ---- Step 3: rank and explain (if Gemini is only busy, show plain results) ----
    try:
        ranked = gemini_service.rank_products(body.message, req, plist)
    except gemini_service.GeminiError as e:
        if e.status_code != 503:
            db.rollback()
            raise HTTPException(e.status_code, str(e))
        ranked = {"summary": "The AI is busy, so here are the plain search results without explanations. "
                             "Ask again in a minute for a full comparison.",
                  "recommendations": []}

    by_id = {p["id"]: p for p in plist}
    out = []
    for r in ranked["recommendations"]:
        p = dict(by_id[r["product_id"]])
        p["recommendation"] = {"why": r["why"], "pros": r["pros"], "cons": r["cons"]}
        p["over_budget"] = _over_budget(p["price"], max_price)
        out.append(p)
        db.add(AIRecommendation(user_id=user.id, conversation_id=conv.id, product_id=p["id"], reason=r["why"],
                                pros=r["pros"], cons=r["cons"]))
    if not out:  # no explanations available: still show the real products
        out = [{**p, "recommendation": None, "over_budget": _over_budget(p["price"], max_price)} for p in plist[:5]]
    db.add(ShoppingEvent(user_id=user.id, event_type="ai_search",
                         payload={"query": req["search_query"], "results": len(out)}))
    return finish(ranked["summary"] or "Here is what I found.", out, needs_clarification=False, notes=notes)


@router.get("/conversations")
def conversations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(Conversation).where(Conversation.user_id == user.id)
                      .order_by(Conversation.id.desc()).limit(30)).all()
    return [{"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()} for c in rows]


@router.get("/conversations/{conversation_id}")
def conversation(conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.get(Conversation, conversation_id)
    if c is None or c.user_id != user.id:
        raise HTTPException(404, "Conversation not found")
    return {"id": c.id, "title": c.title,
            "messages": [{"role": m.role, "content": m.content, "meta": m.meta} for m in c.messages]}


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.get(Conversation, conversation_id)
    if c is None or c.user_id != user.id:
        raise HTTPException(404, "Conversation not found")
    db.delete(c)
    db.commit()