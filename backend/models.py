import json
from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text

from database import Base


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    doctor_name = Column(String(255), nullable=False, index=True)
    interaction_type = Column(String(100), default="Meeting")
    date = Column(Date, nullable=True)
    time = Column(String(20), nullable=True)
    attendees = Column(String(500), nullable=True)
    topics_discussed = Column(Text, nullable=True)
    products = Column(String(500), nullable=True)
    sentiment = Column(String(50), nullable=True)
    brochure = Column(Boolean, default=False)
    samples = Column(Boolean, default=False)
    materials_shared = Column(Text, nullable=True)
    samples_distributed = Column(Text, nullable=True)
    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    follow_up_date = Column(Date, nullable=True)
    follow_up_status = Column(String(50), default="pending")
    ai_suggested_followups = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def _parse_suggestions(self) -> list[str]:
        if not self.ai_suggested_followups:
            return []
        try:
            data = json.loads(self.ai_suggested_followups)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return [s.strip() for s in self.ai_suggested_followups.split("\n") if s.strip()]

    def to_dict(self) -> dict:
        topics = self.topics_discussed or self.products or ""
        materials = self.materials_shared or ("Brochure shared" if self.brochure else "")
        sample_text = self.samples_distributed or ("Samples provided" if self.samples else "")
        return {
            "id": self.id,
            "doctorName": self.doctor_name or "",
            "interactionType": self.interaction_type or "Meeting",
            "date": self.date.isoformat() if isinstance(self.date, date) else "",
            "time": self.time or "",
            "attendees": self.attendees or "",
            "topicsDiscussed": topics,
            "products": self.products or topics,
            "sentiment": self.sentiment or "",
            "brochure": bool(self.brochure),
            "samples": bool(self.samples),
            "materialsShared": materials,
            "samplesDistributed": sample_text,
            "outcomes": self.outcomes or "",
            "followUpActions": self.follow_up_actions or "",
            "notes": self.notes or topics,
            "followUpDate": self.follow_up_date.isoformat()
            if isinstance(self.follow_up_date, date)
            else "",
            "followUpStatus": self.follow_up_status or "pending",
            "aiSuggestedFollowups": self._parse_suggestions(),
            "createdAt": self.created_at.isoformat() if self.created_at else "",
        }
