from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import ShoppingEvent, User
from ..schemas import VoiceCommandIn
from ..services.voice_command_service import execute_command, parse_command
from ..services.voice_service import SUPPORTED_LANGUAGES

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.get("/languages")
def languages():
    return {"languages": SUPPORTED_LANGUAGES,
            "notes": "Speech recognition and speech output run in your browser (Chrome/Edge work best) and need an internet "
                     "connection. Offline voice is not supported. Typed commands always work."}


@router.post("/command")
def command(body: VoiceCommandIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    parsed = parse_command(body.text, body.language)
    result = execute_command(db, user, parsed, body.context)
    db.add(ShoppingEvent(user_id=user.id, event_type="voice_command", payload={"intent": parsed.intent}))
    db.commit()
    return result
