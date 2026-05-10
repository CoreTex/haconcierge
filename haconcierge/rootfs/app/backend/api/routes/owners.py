from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from database.db import get_db
from database.models import Owner, Keyword

router = APIRouter(prefix="/api/owners", tags=["owners"])


class OwnerCreate(BaseModel):
    name: str
    phone: str
    aliases: list[str] = []
    o365_email: Optional[str] = None
    notify_on_task: bool = True
    notify_on_appointment: bool = True
    notify_on_keyword: bool = True


class OwnerUpdate(BaseModel):
    name: Optional[str] = None
    aliases: Optional[list[str]] = None
    o365_email: Optional[str] = None
    notify_on_task: Optional[bool] = None
    notify_on_appointment: Optional[bool] = None
    notify_on_keyword: Optional[bool] = None
    active: Optional[bool] = None


class KeywordCreate(BaseModel):
    word: str
    case_sensitive: bool = False


def _serialize(owner: Owner) -> dict:
    return {
        "id": owner.id,
        "name": owner.name,
        "phone": owner.phone,
        "aliases": owner.aliases or [],
        "o365_email": owner.o365_email,
        "notify_on_task": owner.notify_on_task,
        "notify_on_appointment": owner.notify_on_appointment,
        "notify_on_keyword": owner.notify_on_keyword,
        "active": owner.active,
        "keywords": [
            {"id": k.id, "word": k.word, "case_sensitive": k.case_sensitive, "active": k.active}
            for k in owner.keywords
        ],
    }


@router.get("")
def list_owners(db: Session = Depends(get_db)):
    return [_serialize(o) for o in db.query(Owner).all()]


@router.post("", status_code=201)
def create_owner(body: OwnerCreate, db: Session = Depends(get_db)):
    existing = db.query(Owner).filter(Owner.phone == body.phone).first()
    if existing:
        raise HTTPException(400, "Phone number already exists")
    owner = Owner(**body.model_dump())
    db.add(owner)
    db.commit()
    db.refresh(owner)
    return _serialize(owner)


@router.get("/{owner_id}")
def get_owner(owner_id: int, db: Session = Depends(get_db)):
    owner = db.query(Owner).get(owner_id)
    if not owner:
        raise HTTPException(404, "Owner not found")
    return _serialize(owner)


@router.put("/{owner_id}")
def update_owner(owner_id: int, body: OwnerUpdate, db: Session = Depends(get_db)):
    owner = db.query(Owner).get(owner_id)
    if not owner:
        raise HTTPException(404, "Owner not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(owner, field, value)
    db.commit()
    db.refresh(owner)
    return _serialize(owner)


@router.delete("/{owner_id}", status_code=204)
def delete_owner(owner_id: int, db: Session = Depends(get_db)):
    owner = db.query(Owner).get(owner_id)
    if not owner:
        raise HTTPException(404, "Owner not found")
    db.delete(owner)
    db.commit()


@router.post("/{owner_id}/keywords", status_code=201)
def add_keyword(owner_id: int, body: KeywordCreate, db: Session = Depends(get_db)):
    owner = db.query(Owner).get(owner_id)
    if not owner:
        raise HTTPException(404, "Owner not found")
    kw = Keyword(owner_id=owner_id, word=body.word, case_sensitive=body.case_sensitive)
    db.add(kw)
    db.commit()
    db.refresh(kw)
    return {"id": kw.id, "word": kw.word, "case_sensitive": kw.case_sensitive, "active": kw.active}


@router.delete("/{owner_id}/keywords/{kw_id}", status_code=204)
def delete_keyword(owner_id: int, kw_id: int, db: Session = Depends(get_db)):
    kw = db.query(Keyword).filter(Keyword.id == kw_id, Keyword.owner_id == owner_id).first()
    if not kw:
        raise HTTPException(404, "Keyword not found")
    db.delete(kw)
    db.commit()
