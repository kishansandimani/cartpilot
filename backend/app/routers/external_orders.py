"""Orders made on other stores. Imported ONLY by the user (manual entry or an uploaded receipt). No scraping."""
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import ConnectedAccount, ExternalOrder, ExternalOrderItem, ReceiptImport, User, utcnow
from ..schemas import ManualOrderIn, ReceiptTextIn
from ..services.receipt_parser import parse_receipt_text

router = APIRouter(prefix="/api/external-orders", tags=["external-orders"])
MAX_UPLOAD = 1_000_000


def _parse_and_store(db: Session, user: User, filename: str, text: str) -> dict:
    parsed = parse_receipt_text(text)
    row = ReceiptImport(user_id=user.id, filename=filename[:255], source="upload", status="parsed", parsed=parsed)
    db.add(row)
    db.commit()
    return {"receipt_import_id": row.id, "parsed": parsed,
            "message": "Please review these values - fields we could not read are empty. Nothing is saved until you confirm."}


@router.post("/receipts/parse")
async def parse_upload(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    name = (file.filename or "receipt").lower()
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "File is larger than 1 MB")
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            text = "\n".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(data)).pages[:10])
        except ImportError:
            raise HTTPException(415, "PDF support needs the 'pypdf' package (pip install pypdf).")
        except Exception:
            raise HTTPException(422, "Could not read this PDF.")
        if not text.strip():
            raise HTTPException(422, "This PDF has no readable text (it may be a scan). Please enter the order manually.")
    elif name.endswith((".txt", ".eml", ".html", ".htm")):
        text = data.decode("utf-8", errors="replace")
    else:
        raise HTTPException(415, "Supported receipt files: .txt, .eml, .html, .pdf")
    return _parse_and_store(db, user, name, text)


@router.post("/receipts/parse-text")
def parse_pasted(body: ReceiptTextIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _parse_and_store(db, user, "pasted-text", body.text)


@router.post("", status_code=201)
def create(body: ManualOrderIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    exists = db.scalar(select(ExternalOrder).where(ExternalOrder.user_id == user.id, ExternalOrder.platform == body.platform,
                                                   ExternalOrder.external_order_id == body.external_order_id))
    if exists:
        raise HTTPException(409, "This order was already imported (same platform and order ID).")
    receipt = None
    if body.receipt_import_id:
        receipt = db.get(ReceiptImport, body.receipt_import_id)
        if receipt is None or receipt.user_id != user.id:
            raise HTTPException(404, "Receipt import not found")
    order = ExternalOrder(
        user_id=user.id, platform=body.platform, external_order_id=body.external_order_id,
        order_date=datetime(body.order_date.year, body.order_date.month, body.order_date.day, tzinfo=timezone.utc),
        total=body.total, currency=body.currency, status=body.status, payment_method=body.payment_method,
        tracking_info=body.tracking_info, import_source="receipt_upload" if receipt else "manual",
        receipt_import_id=receipt.id if receipt else None)
    order.items.append(ExternalOrderItem(title=body.product_name, category=body.category, image_url=body.image_url,
                                         price=body.total, quantity=1))
    db.add(order)
    if receipt:
        receipt.status = "confirmed"
    acct = db.scalar(select(ConnectedAccount).where(ConnectedAccount.user_id == user.id, ConnectedAccount.platform == body.platform))
    if acct:
        acct.last_synced_at = utcnow()
    try:
        db.commit()
    except IntegrityError:  # two requests at once: the database unique constraint is the final guard
        db.rollback()
        raise HTTPException(409, "This order was already imported (same platform and order ID).")
    return {"id": order.id, "platform": order.platform, "external_order_id": order.external_order_id}


@router.get("")
def list_external(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(ExternalOrder).where(ExternalOrder.user_id == user.id).order_by(ExternalOrder.order_date.desc())).all()
    return [{"id": r.id, "platform": r.platform, "external_order_id": r.external_order_id, "total": str(r.total),
             "currency": r.currency, "order_date": r.order_date.isoformat(), "import_source": r.import_source,
             "status": r.status, "product_name": r.items[0].title if r.items else None} for r in rows]


@router.delete("/{order_id}", status_code=204)
def delete(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(ExternalOrder, order_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(404, "Order not found")
    db.delete(row)
    db.commit()
