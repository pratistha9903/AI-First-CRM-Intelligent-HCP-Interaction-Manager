from typing import Any

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from agent.state import AgentState
from agent.tools import (
    detect_intent,
    tool_confirm_save,
    tool_edit_interaction,
    tool_log_interaction,
    tool_save_interaction,
    tool_schedule_followup,
    tool_search_interaction,
    tool_summarize_interaction,
    tool_undo,
    _empty_interaction,
)


def build_agent_graph(db: Session):
    """Build and compile the LangGraph agent for HCP interaction management."""

    def receive_message(state: AgentState) -> AgentState:
        return state

    def analyze_intent(state: AgentState) -> AgentState:
        current = state.get("current_interaction") or {}
        has_form_data = bool(current.get("doctorName", "").strip())
        intent = detect_intent(
            state["user_message"],
            state.get("conversation_history", []),
            pending_confirmation=state.get("pending_confirmation", False),
            has_form_data=has_form_data,
        )
        return {**state, "intent": intent}

    def route_intent(state: AgentState) -> str:
        return state.get("intent", "general")

    def run_tool(state: AgentState) -> AgentState:
        intent = state.get("intent", "general")
        message = state["user_message"]
        current = state.get("current_interaction") or _empty_interaction()
        undo_stack = state.get("undo_stack") or []

        if intent == "confirm":
            # Always save exactly what is on the form right now
            payload = dict(current)
            result = tool_save_interaction(payload, db)
            return {
                **state,
                "tool_name": "confirm_save",
                "tool_result": result,
                "reply": result["reply"],
                "interaction": result.get("interaction", current),
                "pending_confirmation": False,
                "pending_payload": {},
                "db_interaction_id": result.get("db_interaction_id"),
            }

        if state.get("pending_confirmation") and intent == "cancel":
            return {
                **state,
                "tool_name": "cancel",
                "reply": "Save cancelled. You can continue editing or start a new interaction.",
                "interaction": current,
                "pending_confirmation": False,
                "pending_payload": {},
            }

        tool_map = {
            "log_interaction": lambda: tool_log_interaction(message, current, db),
            "edit_interaction": lambda: tool_edit_interaction(message, current, db),
            "search_interaction": lambda: tool_search_interaction(message, db),
            "summarize_interaction": lambda: tool_summarize_interaction(
                message, current, db
            ),
            "schedule_followup": lambda: tool_schedule_followup(message, current, db),
            "undo": lambda: tool_undo(undo_stack),
        }

        if intent in tool_map:
            result = tool_map[intent]()
            new_state: dict[str, Any] = {
                **state,
                "tool_name": intent,
                "tool_result": result,
                "reply": result.get("reply", ""),
                "interaction": result.get("interaction", current),
                "requires_input": result.get("requires_input", False),
            }

            if result.get("requires_confirmation"):
                new_state["pending_confirmation"] = True
                new_state["pending_payload"] = result.get("pending_payload", {})

            if result.get("pending_payload") is not None and intent == "edit_interaction":
                new_state["pending_payload"] = result["pending_payload"]
                if state.get("pending_confirmation"):
                    new_state["pending_confirmation"] = True

            if result.get("undo_snapshot"):
                new_stack = list(undo_stack) + [result["undo_snapshot"]]
                new_state["undo_stack"] = new_stack

            if result.get("pop_undo"):
                new_state["undo_stack"] = undo_stack[:-1]

            return new_state

        greetings = ("hello", "hi", "hey", "help")
        if any(message.lower().strip().startswith(g) for g in greetings):
            reply = (
                "Hello! I'm your HCP Interaction Assistant. I can help you:\n"
                "• Log a new visit (e.g. 'Today I met Dr. Smith...')\n"
                "• Edit fields (e.g. 'Change sentiment to negative')\n"
                "• Search past meetings (e.g. 'Show my last meeting with Dr. Smith')\n"
                "• Summarize visits\n"
                "• Schedule follow-ups (e.g. 'Schedule follow-up next Monday')\n"
                "• Undo changes (e.g. 'Undo the previous change')"
            )
        else:
            reply = (
                "I'm not sure what you'd like to do. Try logging an interaction, "
                "editing a field, searching, summarizing, or scheduling a follow-up."
            )

        return {
            **state,
            "tool_name": "general",
            "reply": reply,
            "interaction": current,
        }

    def format_response(state: AgentState) -> AgentState:
        return state

    graph = StateGraph(AgentState)
    graph.add_node("receive_message", receive_message)
    graph.add_node("analyze_intent", analyze_intent)
    graph.add_node("run_tool", run_tool)
    graph.add_node("format_response", format_response)

    graph.set_entry_point("receive_message")
    graph.add_edge("receive_message", "analyze_intent")
    graph.add_edge("analyze_intent", "run_tool")
    graph.add_edge("run_tool", "format_response")
    graph.add_edge("format_response", END)

    return graph.compile()


_session_memory: dict[str, dict] = {}


def run_agent(
    message: str,
    session_id: str,
    current_interaction: dict,
    pending_confirmation: bool,
    conversation_history: list,
    db: Session,
) -> dict[str, Any]:
    memory = _session_memory.get(session_id, {})
    undo_stack = memory.get("undo_stack", [])
    pending_payload = memory.get("pending_payload", {})

    graph = build_agent_graph(db)
    initial_state: AgentState = {
        "user_message": message,
        "session_id": session_id,
        "current_interaction": current_interaction,
        "conversation_history": conversation_history,
        "pending_confirmation": pending_confirmation,
        "pending_payload": pending_payload,
        "undo_stack": undo_stack,
    }

    final_state = graph.invoke(initial_state)

    _session_memory[session_id] = {
        "undo_stack": final_state.get("undo_stack", undo_stack),
        "pending_payload": final_state.get("pending_payload", {}),
    }

    return {
        "reply": final_state.get("reply", ""),
        "interaction": final_state.get("interaction", current_interaction),
        "pending_confirmation": final_state.get("pending_confirmation", False),
        "tool_used": final_state.get("tool_name"),
        "requires_input": final_state.get("requires_input", False),
    }
