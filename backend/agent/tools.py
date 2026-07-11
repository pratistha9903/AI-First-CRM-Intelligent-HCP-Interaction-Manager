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
    now = datetime.now()
    return {
        "id": None,
        "doctorName": "",
        "interactionType": "Meeting",
        "date": "",
        "time": now.strftime("%H:%M"),
        "attendees": "",
        "topicsDiscussed": "",
        "products": "",
        "sentiment": "neutral",
        "brochure": False,
        "samples": False,
        "materialsShared": "",
        "samplesDistributed": "",
        "outcomes": "",
        "followUpActions": "",
        "notes": "",
        "followUpDate": "",
        "followUpStatus": "pending",
        "aiSuggestedFollowups": [],
    }


def _suggest_followups(merged: dict) -> list[str]:
    suggestions = []
    doctor = merged.get("doctorName") or "HCP"
    product = merged.get("products") or merged.get("topicsDiscussed") or "product"
    if not merged.get("followUpDate"):
        suggestions.append("Schedule follow-up meeting in 2 weeks")
    suggestions.append(f"Send {product} information PDF")
    suggestions.append(f"Add {doctor} to advisory board invite list")
    return suggestions[:3]


def _apply_payload_to_record(record: Interaction, payload: dict) -> None:
    topics = payload.get("topicsDiscussed") or payload.get("notes") or payload.get("products") or ""
    materials = payload.get("materialsShared") or ""
    sample_text = payload.get("samplesDistributed") or ""
    suggestions = payload.get("aiSuggestedFollowups") or _suggest_followups(payload)

    record.doctor_name = payload.get("doctorName", "").strip()
    record.interaction_type = payload.get("interactionType") or "Meeting"
    record.date = _parse_date(payload.get("date", ""))
    record.time = payload.get("time") or None
    record.attendees = payload.get("attendees") or ""
    record.topics_discussed = topics
    record.products = payload.get("products") or topics
    record.sentiment = (payload.get("sentiment") or "neutral").lower()
    record.brochure = bool(payload.get("brochure", False)) or bool(materials)
    record.samples = bool(payload.get("samples", False)) or bool(sample_text)
    record.materials_shared = materials
    record.samples_distributed = sample_text
    record.outcomes = payload.get("outcomes") or ""
    record.follow_up_actions = payload.get("followUpActions") or ""
    record.notes = payload.get("notes") or topics
    record.follow_up_date = _parse_date(payload.get("followUpDate", ""))
    record.follow_up_status = payload.get("followUpStatus") or "pending"
    record.ai_suggested_followups = json.dumps(suggestions)


def _build_notes(message: str, extracted: dict, merged: dict) -> str:
    notes = (extracted.get("notes") or merged.get("notes") or "").strip()
    topics = (extracted.get("topicsDiscussed") or merged.get("topicsDiscussed") or "").strip()
    if topics and not notes:
        return topics
    if notes:
        return notes
    return message.strip()


def _merge_interaction(current: dict, updates: dict) -> dict:
    merged = {**_empty_interaction(), **current}
    for key, value in updates.items():
        if value is not None and value != "":
            merged[key] = value
    return merged


def _resolve_log_date(extracted_date: str, message: str, today: str) -> str:
    """Default visit date to today unless user clearly gave another date."""
    if extracted_date:
        lowered = str(extracted_date).strip().lower()
        if lowered in ("today", "todays", "now"):
            return today
        parsed = _parse_date(extracted_date)
        if parsed:
            return parsed.isoformat()

    lowered_msg = message.lower()
    if any(word in lowered_msg for word in ("today", "this morning", "this afternoon", "just met", "just visited")):
        return today

    # No date mentioned — default to today for new visit logs
    return today


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


def _normalize_doctor_name(name: str) -> str:
    if not name:
        return ""
    cleaned = name.strip()
    for prefix in ("dr.", "dr", "doctor", "prof.", "prof"):
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):].strip(" .")
            break
    return cleaned


def _looks_like_log(message: str) -> bool:
    text = message.lower()
    log_signals = (
        "i met", "met dr", "met doctor", "today i met", "today i meet",
        "discussed", "we talked", "we talk", "visited", "positive sentiment",
        "negative sentiment", "shared brochure", "samples", "discussed product",
    )
    return any(s in text for s in log_signals)


def _quick_schedule_intent(message: str) -> Optional[str]:
    # Full visit logs may mention follow-ups — let log_interaction handle those
    if _looks_like_log(message):
        return None

    text = message.lower()
    schedule_phrases = (
        "follow-up", "follow up", "followup",
        "next meeting", "next visit",
        "schedule follow", "set follow up", "set follow-up",
    )
    if any(p in text for p in schedule_phrases):
        return "schedule_followup"
    if "tomorrow" in text and any(w in text for w in ("meeting", "visit", "follow", "next")):
        return "schedule_followup"
    return None


def _parse_relative_followup_date(message: str, today: date) -> Optional[str]:
    """Parse common relative follow-up phrases without relying on the LLM."""
    text = message.lower()

    if "day after tomorrow" in text:
        return (today + timedelta(days=2)).isoformat()
    if "tomorrow" in text:
        return (today + timedelta(days=1)).isoformat()
    if "next week" in text or "in a week" in text or "in 1 week" in text:
        return (today + timedelta(days=7)).isoformat()
    if "in two weeks" in text or "in 2 weeks" in text:
        return (today + timedelta(days=14)).isoformat()

    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
    }
    for name, weekday in weekdays.items():
        if f"next {name}" in text:
            days_ahead = (weekday - today.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (today + timedelta(days=days_ahead)).isoformat()

    return None


def _quick_intent(message: str, pending_confirmation: bool, has_form_data: bool = False) -> Optional[str]:
    text = message.strip().lower()
    save_phrases = (
        "yes", "y", "yeah", "yep", "ok", "okay", "save", "confirm",
        "go ahead", "correct", "sure", "do it", "save it",
        "save to database", "save the data", "store", "store it",
        "save this", "save changes", "update database", "persist",
    )
    cancel_words = {"no", "n", "nope", "cancel", "don't save", "dont save", "stop"}

    wants_save = text in save_phrases or any(
        text.startswith(p + " ") or text == p for p in save_phrases
    ) or "save" in text and ("database" in text or "data" in text or "changes" in text)

    if pending_confirmation and wants_save:
        return "confirm"
    if pending_confirmation and (text in cancel_words or text.startswith("no ")):
        return "cancel"
    # Allow save even after edits when form has data but pending flag was lost
    if has_form_data and wants_save and not pending_confirmation:
        return "confirm"
    return None


def detect_intent(
    message: str, history: list[dict], pending_confirmation: bool = False, has_form_data: bool = False
) -> str:
    schedule = _quick_schedule_intent(message)
    if schedule:
        return schedule

    quick = _quick_intent(message, pending_confirmation, has_form_data)
    if quick:
        return quick

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
    now_time = datetime.now().strftime("%H:%M")
    prompt = LOG_INTERACTION_PROMPT.format(today=today, now_time=now_time) + f"\n\nUser message: {message}"
    response = llm.invoke(prompt)
    extracted = _parse_json(response.content)

    # New visit — do not merge with a previously saved interaction (keeps old id/data)
    if current.get("id"):
        base = _empty_interaction()
    else:
        base = {**_empty_interaction(), **current}
        base["id"] = None

    merged = _merge_interaction(base, extracted)
    merged["id"] = None
    merged["date"] = _resolve_log_date(extracted.get("date", ""), message, today)

    # Follow-up date if mentioned in the same log message
    follow_up = extracted.get("followUpDate", "")
    if not follow_up and _quick_schedule_intent(message):
        follow_up = _parse_relative_followup_date(message, date.today()) or ""
    if follow_up:
        parsed_follow = _parse_date(follow_up)
        merged["followUpDate"] = parsed_follow.isoformat() if parsed_follow else follow_up
        merged["followUpStatus"] = "scheduled"

    merged["notes"] = _build_notes(message, extracted, merged)
    if not merged.get("topicsDiscussed"):
        merged["topicsDiscussed"] = merged["notes"] or merged.get("products", "")
    if not merged.get("time"):
        merged["time"] = now_time
    if not merged.get("interactionType"):
        merged["interactionType"] = "Meeting"
    if not merged.get("sentiment"):
        merged["sentiment"] = "neutral"
    merged["aiSuggestedFollowups"] = _suggest_followups(merged)

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
    confirmation += "\n\n⚠️ Not saved yet — type **YES** to save to the database."
    return {
        "success": True,
        "requires_confirmation": True,
        "interaction": merged,
        "reply": confirmation,
        "pending_payload": merged,
    }


def tool_save_interaction(payload: dict, db: Session) -> dict[str, Any]:
    """Save the current form — update if record exists, insert if new."""
    missing = _validate_interaction(payload)
    if missing:
        return {
            "success": False,
            "reply": f"Cannot save — missing or invalid: {', '.join(missing)}",
            "interaction": payload,
        }

    record_id = payload.get("id")
    if record_id:
        db_record = db.query(Interaction).filter(Interaction.id == record_id).first()
        if db_record:
            _apply_payload_to_record(db_record, payload)
            db.commit()
            db.refresh(db_record)
            saved = db_record.to_dict()
            return {
                "success": True,
                "interaction": saved,
                "reply": f"Updated record #{saved['id']} in database: {saved['doctorName']}.",
                "db_interaction_id": db_record.id,
            }

    return tool_confirm_save(payload, db)


def tool_confirm_save(payload: dict, db: Session) -> dict[str, Any]:
    missing = _validate_interaction(payload)
    if missing:
        return {
            "success": False,
            "reply": f"Cannot save — missing or invalid: {', '.join(missing)}",
            "interaction": payload,
        }

    interaction = Interaction()
    _apply_payload_to_record(interaction, payload)
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    saved = interaction.to_dict()
    return {
        "success": True,
        "interaction": saved,
        "reply": (
            f"Saved to database as record #{saved['id']}: "
            f"{saved['doctorName']} on {saved['date'] or 'N/A'}."
        ),
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
        elif field == "notes" and current.get("notes") and value:
            # Append new note to existing notes
            existing = current.get("notes", "").strip()
            new_val = str(value).strip()
            if existing and new_val and new_val not in existing:
                updated[field] = f"{existing}\n{new_val}"
            else:
                updated[field] = new_val or existing
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
            _apply_payload_to_record(db_record, updated)
            db.commit()
            db.refresh(db_record)
            updated = db_record.to_dict()

    explanation = result.get("explanation", "Updated the interaction.")
    saved_note = ""
    if updated.get("id"):
        saved_note = " Changes saved to database."
    elif current.get("doctorName") or updated.get("doctorName"):
        saved_note = " Form updated (not in database yet — type SAVE or YES when ready)."

    return {
        "success": True,
        "interaction": updated,
        "reply": f"{explanation}{saved_note}",
        "undo_snapshot": previous,
        "pending_payload": updated,
    }


def _query_interactions(db: Session, doctor_name: str, limit: int = 1):
    normalized = _normalize_doctor_name(doctor_name)
    if not normalized:
        return []

    # Try exact/partial match on normalized name
    results = (
        db.query(Interaction)
        .filter(
            (Interaction.doctor_name.ilike(f"%{normalized}%"))
            | (Interaction.doctor_name.ilike(f"%{doctor_name.strip()}%"))
        )
        .order_by(Interaction.created_at.desc(), Interaction.date.desc())
        .limit(limit)
        .all()
    )
    return results


def tool_search_interaction(message: str, db: Session) -> dict[str, Any]:
    llm = get_llm()
    prompt = SEARCH_INTERACTION_PROMPT + f"\n\nUser message: {message}"
    response = llm.invoke(prompt)
    params = _parse_json(response.content)

    doctor_name = params.get("doctorName", "").strip()
    limit = int(params.get("limit", 1))

    if not doctor_name:
        recent = (
            db.query(Interaction)
            .order_by(Interaction.created_at.desc(), Interaction.date.desc())
            .limit(5)
            .all()
        )
        if not recent:
            return {
                "success": False,
                "reply": "No saved interactions in the database yet. Log a visit and type YES to save it first.",
                "interaction": _empty_interaction(),
            }
        lines = ["Recent saved interactions:"]
        for r in recent:
            lines.append(f"  • {r.doctor_name} — {r.date or 'N/A'} — {r.products or 'N/A'}")
        lines.append("\nAsk: 'Show my last meeting with <doctor name>'")
        return {
            "success": True,
            "interaction": recent[0].to_dict(),
            "reply": "\n".join(lines),
        }

    results = _query_interactions(db, doctor_name, limit)

    if not results:
        recent = (
            db.query(Interaction)
            .order_by(Interaction.created_at.desc(), Interaction.date.desc())
            .limit(3)
            .all()
        )
        reply = f"No interactions found for {doctor_name}."
        if recent:
            names = ", ".join(r.doctor_name for r in recent)
            reply += f"\n\nSaved doctors in database: {names}\nTry searching with the exact name you used when saving."
        else:
            reply += "\n\nNo data saved yet. After logging a visit, type YES to save it to the database."
        return {
            "success": False,
            "reply": reply,
            "interaction": _empty_interaction(),
        }

    found = results[0].to_dict()
    reply_lines = [
        f"Found record #{found['id']} — {found['doctorName']}:",
        f"  Date: {found['date'] or 'N/A'}",
        f"  Products: {found['products'] or 'N/A'}",
        f"  Sentiment: {found['sentiment'] or 'N/A'}",
        f"  Brochure: {'Yes' if found['brochure'] else 'No'}",
        f"  Samples: {'Yes' if found['samples'] else 'No'}",
        f"  Follow-up: {found['followUpDate'] or 'N/A'} ({found['followUpStatus'] or 'pending'})",
        f"  Notes: {found['notes'] or 'N/A'}",
        "",
        "Loaded into the form. You can edit fields or ask for a summary.",
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
            results = _query_interactions(db, doctor_name, 1)
            if results:
                interaction_data = results[0].to_dict()

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
    today_date = date.today()
    today = today_date.isoformat()

    # Try local parsing first (reliable for tomorrow, next Monday, etc.)
    follow_up_date = _parse_relative_followup_date(message, today_date) or ""

    schedule = {"followUpStatus": "scheduled", "reminderNote": ""}
    if not follow_up_date:
        llm = get_llm()
        prompt = SCHEDULE_FOLLOWUP_PROMPT.format(today=today) + f"\n\nUser message: {message}"
        response = llm.invoke(prompt)
        schedule = _parse_json(response.content)
        follow_up_date = schedule.get("followUpDate", "")

    if not follow_up_date:
        return {
            "success": False,
            "reply": "I couldn't determine the follow-up date. Try: 'Schedule follow-up tomorrow' or 'Next meeting is tomorrow'.",
            "interaction": current,
        }

    parsed = _parse_date(follow_up_date)
    if parsed:
        follow_up_date = parsed.isoformat()

    updated = {**_empty_interaction(), **current}
    updated["followUpDate"] = follow_up_date
    updated["followUpStatus"] = schedule.get("followUpStatus", "scheduled")
    action_text = schedule.get("reminderNote") or f"Follow-up meeting on {follow_up_date}"
    updated["followUpActions"] = action_text

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
