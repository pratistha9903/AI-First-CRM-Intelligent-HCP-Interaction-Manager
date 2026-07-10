from typing import Any, Optional

from pydantic import BaseModel, Field


class InteractionBase(BaseModel):
    doctor_name: str = Field("", alias="doctorName")
    date: Optional[str] = ""
    products: str = ""
    sentiment: str = ""
    brochure: bool = False
    samples: bool = False
    notes: str = ""
    follow_up_date: Optional[str] = Field("", alias="followUpDate")
    follow_up_status: str = Field("pending", alias="followUpStatus")

    model_config = {"populate_by_name": True}


class InteractionCreate(InteractionBase):
    pass


class InteractionUpdate(InteractionBase):
    doctor_name: Optional[str] = Field(None, alias="doctorName")
    products: Optional[str] = None
    sentiment: Optional[str] = None
    brochure: Optional[bool] = None
    samples: Optional[bool] = None
    notes: Optional[str] = None
    follow_up_date: Optional[str] = Field(None, alias="followUpDate")
    follow_up_status: Optional[str] = Field(None, alias="followUpStatus")


class InteractionResponse(InteractionBase):
    id: int
    created_at: Optional[str] = Field("", alias="createdAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
  # Current interaction context from frontend Redux state
    current_interaction: dict[str, Any] = Field(default_factory=dict)
    pending_confirmation: bool = False
    conversation_history: list[dict[str, str]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    interaction: dict[str, Any]
    pending_confirmation: bool = False
    tool_used: Optional[str] = None
    requires_input: bool = False
