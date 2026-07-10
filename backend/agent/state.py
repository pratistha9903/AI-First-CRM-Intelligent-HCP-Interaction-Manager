from typing import Any, Optional, TypedDict


class AgentState(TypedDict, total=False):
    user_message: str
    session_id: str
    current_interaction: dict[str, Any]
    conversation_history: list[dict[str, str]]
    pending_confirmation: bool
    pending_payload: dict[str, Any]
    intent: str
    tool_name: str
    tool_result: dict[str, Any]
    reply: str
    interaction: dict[str, Any]
    requires_input: bool
    undo_stack: list[dict[str, Any]]
    db_interaction_id: Optional[int]
