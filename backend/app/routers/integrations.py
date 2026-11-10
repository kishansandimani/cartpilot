"""Connected platforms. We only claim what is real:
 * Amazon/Flipkart/Myntra/AJIO do not offer customers' order history through a public API, so the supported
   integration is user-driven import (receipt upload / manual entry). No passwords, no scraping.
 * A platform becomes an 'official_api' integration only when a customer-authorized API adapter exists.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import ConnectedAccount, ExternalOrder, User

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

CATALOG = {
    "amazon": "Amazon", "flipkart": "Flipkart", "myntra": "Myntra", "ajio": "AJIO",
}
IMPORT_PERMISSIONS = ["Manual order entry (you type it)", "Receipt upload (.txt, .eml, .html, .pdf you choose)"]
NO_API_REASON = "No public customer order-history API is available, so CartPilot cannot read this account directly."


@router.get("")
def list_integrations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    accts = {a.platform: a for a in db.scalars(select(ConnectedAccount).where(ConnectedAccount.user_id == user.id))}
    counts = dict(db.execute(select(ExternalOrder.platform, func.count()).where(ExternalOrder.user_id == user.id)
                             .group_by(ExternalOrder.platform)).all())
    out = [{"platform": "cartpilot", "name": "CartPilot (PayPal)", "integration_type": "paypal_checkout", "status": "active",
            "built_in": True, "permissions": ["Checkout and order tracking inside CartPilot"],
            "last_synced_at": None, "order_count": None, "official_api": {"available": True, "reason": None}}]
    for key, name in CATALOG.items():
        a = accts.get(key)
        out.append({"platform": key, "name": name, "integration_type": "manual_receipts",
                    "status": "active" if a else "not_connected", "built_in": False,
                    "permissions": IMPORT_PERMISSIONS if a else [],
                    "last_synced_at": a.last_synced_at.isoformat() if a and a.last_synced_at else None,
                    "order_count": counts.get(key, 0), "official_api": {"available": False, "reason": NO_API_REASON}})
    return {"platforms": out,
            "email_import": {"available": False,
                             "reason": "Email receipt import needs Gmail OAuth credentials, which are not set up in this build. "
                                       "Use receipt upload or manual entry."}}


@router.post("/{platform}/connect", status_code=201)
def connect(platform: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if platform not in CATALOG:
        raise HTTPException(404, "Unknown platform")
    if db.scalar(select(ConnectedAccount).where(ConnectedAccount.user_id == user.id, ConnectedAccount.platform == platform)):
        raise HTTPException(409, "Already enabled")
    db.add(ConnectedAccount(user_id=user.id, platform=platform, integration_type="manual_receipts", status="active",
                            permissions=IMPORT_PERMISSIONS))
    db.commit()
    return {"platform": platform, "status": "active"}


@router.delete("/{platform}", status_code=204)
def disconnect(platform: str, delete_orders: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    acct = db.scalar(select(ConnectedAccount).where(ConnectedAccount.user_id == user.id, ConnectedAccount.platform == platform))
    if acct is None:
        raise HTTPException(404, "Not connected")
    db.delete(acct)
    if delete_orders:
        for o in db.scalars(select(ExternalOrder).where(ExternalOrder.user_id == user.id, ExternalOrder.platform == platform)):
            db.delete(o)
    db.commit()
