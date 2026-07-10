from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text

from database import Base


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    doctor_name = Column(String(255), nullable=False, index=True)
    date = Column(Date, nullable=True)
    products = Column(String(500), nullable=True)
    sentiment = Column(String(50), nullable=True)
    brochure = Column(Boolean, default=False)
    samples = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    follow_up_date = Column(Date, nullable=True)
    follow_up_status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "doctorName": self.doctor_name or "",
            "date": self.date.isoformat() if isinstance(self.date, date) else "",
            "products": self.products or "",
            "sentiment": self.sentiment or "",
            "brochure": bool(self.brochure),
            "samples": bool(self.samples),
            "notes": self.notes or "",
            "followUpDate": self.follow_up_date.isoformat()
            if isinstance(self.follow_up_date, date)
            else "",
            "followUpStatus": self.follow_up_status or "pending",
            "createdAt": self.created_at.isoformat() if self.created_at else "",
        }
