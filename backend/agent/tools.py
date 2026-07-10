import json
import re
from datetime import date, datetime, timedelta
from typing import Any, Optional

from dateutil import parser as date_parser
from langchain_groq import ChatGroq
from sqlalchemy.orm import Session

from agent.prompts import (
    CONFIRMATION_PROMPT,
    EDIT_INTERACTION_PROMPT,
    INTENT_DETECTION_PROMPT,
    LOG_INTERACTION_PROMPT,
    MISSING_INFO_PROMPT,
    SCHEDULE_FOLLOWUP_PROMPT,
    SEARCH_INTERACTION_PROMPT,
    SUMMARIZE_INTERACTION_PROMPT,
)
from config import settings
from models import Interaction


def get_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model_name=settings.groq_model,
        temperature=0.1,
    )


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())
        raise


def _parse_date(value: str) -> Optional[date]:
    if not value:
        return None
    try:
        return date_parser.parse(value).date()
    except (ValueError, TypeError):
        return None


def _empty_interaction() -> dict[str, Any]:
    return {
        "id": None,
        "doctorName": "",
        "date": "",
        "products": "",
        "sentiment": "",
        "brochure": False,
        "samples": False,
        "notes": "",
        "followUpDate": "",
        "followUpStatus": "pending",
    }


def _merge_interaction(current: dict, updates: dict) -> dict:
    merged = {**_empty_interaction(), **current}
    for key, value in updates.items():
        if value is not None and value != "":
            merged[key] = value
    return merged


def _validate_interaction(data: dict) -> list[str]:
    missing = []
    if not data.get("doctorName", "").strip():
        missing.append("doctorName")
    date_val = data.get("date", "")
    if date_val:
        parsed = _parse_date(date_val)
        if parsed and parsed > date.today():
            missing.append("date (cannot be in the future)")
    sentiment = data.get("sentiment", "").lower()
    if sentiment and sentiment not in ("positive", "negative", "neutral"):
        missing.append("sentiment (must be positive, negative, or neutral)")
    return missing


def detect_intent(message: str, history: list[dict]) -> str:
    llm = get_llm()
    context = ""
    if history:
        recent = history[-4:]
        context = "\nRecent conversation:\n" + "\n".join(
            f"{m['role']}: {m['content']}" for m in recent
        )
    prompt = f"{INTENT_DETECTION_PROMPT}\n{context}\n\nUser message: {message}"
    response = llm.invoke(prompt)
    result = _parse_json(response.content)
    return result.get("intent", "general")


def tool_log_interaction(
    message: str, current: dict, db: Session
) -> dict[str, Any]:
    llm = get_llm()
    today = date.today().isoformat()
    prompt = LOG_INTERACTION_PROMPT.format(today=today) + f"\n\nUser message: {message}"
    response = llm.invoke(prompt)
    extracted = _parse_json(response.content)

    merged = _merge_interaction(current, extracted)
    if not merged.get("date"):
        merged["date"] = today

    missing = _validate_interaction(merged)
    if missing:
        missing_prompt = MISSING_INFO_PROMPT.format(
            extracted=json.dumps(merged, indent=2),
            missing_fields=", ".join(missing),
        )
        question = llm.invoke(missing_prompt).content.strip()
        return {
            "success": False,
            "requires_input": True,
            "interaction": merged,
            "reply": question,
            "pending_payload": merged,
        }

    confirm_prompt = CONFIRMATION_PROMPT.format(
        extracted=json.dumps(merged, indent=2)
    )
    confirmation = llm.invoke(confirm_prompt).content.strip()
    return {
        "success": True,
        "requires_confirmation": True,
        "interaction": merged,
        "reply": confirmation,
        "pending_payload": merged,
    }


def tool_confirm_save(payload: dict, db: Session) -> dict[str, Any]:
    missing = _validate_interaction(payload)
    if missing:
        return {
            "success": False,
            "reply": f"Cannot save — missing or invalid: {', '.join(missing)}",
            "interaction": payload,
        }

    interaction = Interaction(
        doctor_name=payload.get("doctorName", "").strip(),
        date=_parse_date(payload.get("date", "")),
        products=payload.get("products", ""),
        sentiment=payload.get("sentiment", "").lower(),
        brochure=bool(payload.get("brochure", False)),
        samples=bool(payload.get("samples", False)),
        notes=payload.get("notes", ""),
        follow_up_date=_parse_date(payload.get("followUpDate", "")),
        follow_up_status=payload.get("followUpStatus", "pending"),
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    saved = interaction.to_dict()
    return {
        "success": True,
        "interaction": saved,
        "reply": f"Interaction with {saved['doctorName']} saved successfully.",
        "db_interaction_id": interaction.id,
    }


def tool_edit_interaction(
    message: str, current: dict, db: Session
) -> dict[str, Any]:
    llm = get_llm()
    prompt = (
        EDIT_INTERACTION_PROMPT.format(
            current_interaction=json.dumps(current, indent=2)
        )
        + f"\n\nUser message: {message}"
    )
    response = llm.invoke(prompt)
    result = _parse_json(response.content)
    fields = result.get("fields", {})

    if not fields:
        return {
            "success": False,
            "reply": "I couldn't identify which field to update. Please specify, e.g. 'Change sentiment to negative.'",
            "interaction": current,
        }

    previous = dict(current)
    updated = dict(current)
    for field, value in fields.items():
        if field in ("brochure", "samples"):
            updated[field] = str(value).lower() in ("true", "yes", "1")
        else:
            updated[field] = value

    missing = _validate_interaction(updated) if updated.get("doctorName") else []
    if missing and "doctorName" in missing:
        return {
            "success": False,
            "reply": "Doctor name cannot be empty.",
            "interaction": current,
        }

    if updated.get("id"):
        db_record = db.query(Interaction).filter(Interaction.id == updated["id"]).first()
        if db_record:
            if "doctorName" in fields:
                db_record.doctor_name = updated["doctorName"]
            if "date" in fields:
                db_record.date = _parse_date(updated.get("date", ""))
            if "products" in fields:
                db_record.products = updated.get("products", "")
            if "sentiment" in fields:
                db_record.sentiment = updated.get("sentiment", "").lower()
            if "brochure" in fields:
                db_record.brochure = updated.get("brochure", False)
            if "samples" in fields:
                db_record.samples = updated.get("samples", False)
            if "notes" in fields:
                db_record.notes = updated.get("notes", "")
            if "followUpDate" in fields:
                db_record.follow_up_date = _parse_date(updated.get("followUpDate", ""))
            db.commit()
            db.refresh(db_record)
            updated = db_record.to_dict()

    explanation = result.get("explanation", "Updated the interaction.")
    return {
        "success": True,
        "interaction": updated,
        "reply": f"{explanation} Form updated.",
        "undo_snapshot": previous,
    }


def tool_search_interaction(message: str, db: Session) -> dict[str, Any]:
    llm = get_llm()
    prompt = SEARCH_INTERACTION_PROMPT + f"\n\nUser message: {message}"
    response = llm.invoke(prompt)
    params = _parse_json(response.content)

    doctor_name = params.get("doctorName", "").strip()
    if not doctor_name:
        return {
            "success": False,
            "reply": "Which doctor would you like me to search for?",
            "interaction": _empty_interaction(),
        }

    limit = int(params.get("limit", 1))
    query = db.query(Interaction).filter(
        Interaction.doctor_name.ilike(f"%{doctor_name}%")
    )
    if params.get("mostRecent", True):
        query = query.order_by(Interaction.date.desc(), Interaction.created_at.desc())
    results = query.limit(limit).all()

    if not results:
        return {
            "success": False,
            "reply": f"No interactions found for Dr. {doctor_name}.",
            "interaction": _empty_interaction(),
        }

    found = results[0].to_dict()
    reply_lines = [
        f"Found interaction with {found['doctorName']}:",
        f"  Date: {found['date'] or 'N/A'}",
        f"  Products: {found['products'] or 'N/A'}",
        f"  Sentiment: {found['sentiment'] or 'N/A'}",
        f"  Brochure shared: {'Yes' if found['brochure'] else 'No'}",
        f"  Notes: {found['notes'] or 'N/A'}",
    ]
    return {
        "success": True,
        "interaction": found,
        "reply": "\n".join(reply_lines),
    }


def tool_summarize_interaction(
    message: str, current: dict, db: Session
) -> dict[str, Any]:
    interaction_data = current
    if not current.get("doctorName") and current.get("id"):
        record = db.query(Interaction).filter(Interaction.id == current["id"]).first()
        if record:
            interaction_data = record.to_dict()

    if not interaction_data.get("doctorName"):
        llm = get_llm()
        prompt = SEARCH_INTERACTION_PROMPT + f"\n\nUser message: {message}"
        response = llm.invoke(prompt)
        params = _parse_json(response.content)
        doctor_name = params.get("doctorName", "")
        if doctor_name:
            record = (
                db.query(Interaction)
                .filter(Interaction.doctor_name.ilike(f"%{doctor_name}%"))
                .order_by(Interaction.date.desc())
                .first()
            )
            if record:
                interaction_data = record.to_dict()

    if not interaction_data.get("doctorName"):
        return {
            "success": False,
            "reply": "No interaction to summarize. Please log or search for an interaction first.",
            "interaction": current,
        }

    llm = get_llm()
    prompt = SUMMARIZE_INTERACTION_PROMPT.format(
        interaction_data=json.dumps(interaction_data, indent=2)
    )
    summary = llm.invoke(prompt).content.strip()
    return {
        "success": True,
        "interaction": interaction_data,
        "reply": summary,
    }


def tool_schedule_followup(
    message: str, current: dict, db: Session
) -> dict[str, Any]:
    llm = get_llm()
    today = date.today().isoformat()
    prompt = SCHEDULE_FOLLOWUP_PROMPT.format(today=today) + f"\n\nUser message: {message}"
    response = llm.invoke(prompt)
    schedule = _parse_json(response.content)

    follow_up_date = schedule.get("followUpDate", "")
    if not follow_up_date:
        return {
            "success": False,
            "reply": "I couldn't determine the follow-up date. Please specify, e.g. 'Schedule follow-up next Monday.'",
            "interaction": current,
        }

    updated = dict(current)
    updated["followUpDate"] = follow_up_date
    updated["followUpStatus"] = schedule.get("followUpStatus", "scheduled")

    if current.get("id"):
        record = db.query(Interaction).filter(Interaction.id == current["id"]).first()
        if record:
            record.follow_up_date = _parse_date(follow_up_date)
            record.follow_up_status = updated["followUpStatus"]
            if schedule.get("reminderNote"):
                existing_notes = record.notes or ""
                record.notes = (
                    f"{existing_notes}\n[Follow-up reminder: {schedule['reminderNote']}]".strip()
                )
            db.commit()
            db.refresh(record)
            updated = record.to_dict()

    reminder = schedule.get("reminderNote", "")
    reply = f"Follow-up scheduled for {follow_up_date}."
    if reminder:
        reply += f" Reminder: {reminder}"
    return {
        "success": True,
        "interaction": updated,
        "reply": reply,
    }


def tool_undo(undo_stack: list[dict]) -> dict[str, Any]:
    if not undo_stack:
        return {
            "success": False,
            "reply": "Nothing to undo.",
            "interaction": _empty_interaction(),
        }
    previous = undo_stack[-1]
    return {
        "success": True,
        "interaction": previous,
        "reply": "Reverted the previous change.",
        "pop_undo": True,
    }
