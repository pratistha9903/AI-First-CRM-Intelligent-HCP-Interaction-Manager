from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agent.graph import run_agent
from database import get_db
from models import Interaction
from schemas import ChatRequest, ChatResponse, InteractionCreate, InteractionUpdate

router = APIRouter()


def _apply_create(record: Interaction, data: InteractionCreate) -> None:
    record.doctor_name = data.doctor_name
    record.date = date.fromisoformat(data.date) if data.date else None
    record.products = data.products
    record.sentiment = data.sentiment
    record.brochure = data.brochure
    record.samples = data.samples
    record.notes = data.notes
    record.follow_up_date = (
        date.fromisoformat(data.follow_up_date) if data.follow_up_date else None
    )
    record.follow_up_status = data.follow_up_status


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    result = run_agent(
        message=request.message,
        session_id=request.session_id,
        current_interaction=request.current_interaction,
        pending_confirmation=request.pending_confirmation,
        conversation_history=request.conversation_history,
        db=db,
    )

    return ChatResponse(
        reply=result["reply"],
        interaction=result["interaction"],
        pending_confirmation=result.get("pending_confirmation", False),
        tool_used=result.get("tool_used"),
        requires_input=result.get("requires_input", False),
    )


@router.post("/interaction")
def create_interaction(data: InteractionCreate, db: Session = Depends(get_db)):
    if not data.doctor_name.strip():
        raise HTTPException(status_code=400, detail="Doctor name is required")

    record = Interaction()
    _apply_create(record, data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record.to_dict()


@router.get("/interaction/{interaction_id}")
def get_interaction(interaction_id: int, db: Session = Depends(get_db)):
    record = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return record.to_dict()


@router.get("/interaction")
def list_interactions(
    doctor_name: str | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    query = db.query(Interaction).order_by(Interaction.created_at.desc())
    if doctor_name:
        query = query.filter(Interaction.doctor_name.ilike(f"%{doctor_name}%"))
    return [r.to_dict() for r in query.limit(limit).all()]


@router.put("/interaction/{interaction_id}")
def update_interaction(
    interaction_id: int,
    data: InteractionUpdate,
    db: Session = Depends(get_db),
):
    record = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Interaction not found")

    update_data = data.model_dump(exclude_unset=True, by_alias=False)
    field_map = {
        "doctor_name": "doctor_name",
        "date": "date",
        "products": "products",
        "sentiment": "sentiment",
        "brochure": "brochure",
        "samples": "samples",
        "notes": "notes",
        "follow_up_date": "follow_up_date",
        "follow_up_status": "follow_up_status",
    }

    for key, attr in field_map.items():
        if key in update_data and update_data[key] is not None:
            value = update_data[key]
            if key in ("date", "follow_up_date") and value:
                value = date.fromisoformat(value)
            setattr(record, attr, value)

    db.commit()
    db.refresh(record)
    return record.to_dict()


@router.delete("/interaction/{interaction_id}")
def delete_interaction(interaction_id: int, db: Session = Depends(get_db)):
    record = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Interaction not found")
    db.delete(record)
    db.commit()
    return {"message": "Interaction deleted", "id": interaction_id}
