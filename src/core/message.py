from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel

MessageRole = Literal["user", "assistant", "system", "tool"]

class Message(BaseModel):
    content: str
    role: MessageRole
    timestamp: datetime = None
    metadata: Optional[Dict[str, Any]] = None

    def __init__(self, role: MessageRole, content: str, **kwargs):
        super().__init__(role=role, content=content, timestamp=kwargs.get('timestamp', datetime.now()), metadata=kwargs.get('metadata', {}))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
        }

    def __str__(self) -> str:
        return f"[{self.role}] {self.content}"
