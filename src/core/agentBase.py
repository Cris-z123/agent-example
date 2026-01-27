from abc import ABC, abstractmethod
from typing import Optional

from core import GeneralLLMClient

from .config import Config
from .message import Message


class AgentBase(ABC):

    def __init__(self, name: str, llm:GeneralLLMClient, system_prompt: Optional[str] = None, config: Optional[Config] = None):

        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config or Config()
        self._history: list[Message] = []

    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str:
        pass

    def add_message(self, message: Message):
        self._history.append(message)

    def clear_history(self):
        self._history.clear()

    def get_history(self) -> list[Message]:
        return self._history.copy()

    def __str__(self) -> str:
        return f"Agent(name={self.name}, provider={self.llm.provider})"
