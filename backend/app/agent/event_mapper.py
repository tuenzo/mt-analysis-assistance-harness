import json
from datetime import datetime
from app.projects.models import AgentEvent


class EventMapper:
    @staticmethod
    def map_to_agent_event(session_id: str, turn_id: str, project_id: str, raw_event: dict) -> AgentEvent:
        event_type = raw_event.get("type", "unknown")
        payload = json.dumps(raw_event, ensure_ascii=False)

        db = __import__("app.core.database", fromlist=["get_session"]).get_session()
        try:
            event = AgentEvent(
                id=raw_event.get("id", f"evt_{datetime.now().isoformat()}"),
                session_id=session_id,
                turn_id=turn_id,
                project_id=project_id,
                type=event_type,
                payload_json=payload,
                created_at=datetime.now().isoformat(),
            )
            db.add(event)
            db.commit()
            return event
        finally:
            db.close()

    @staticmethod
    def to_sse_format(event: dict) -> str:
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    @staticmethod
    def format_event(type: str, turn_id: str, **kwargs) -> dict:
        return {"type": type, "turn_id": turn_id, **kwargs}
