from abc import ABC, abstractmethod
from ast import List
from typing import Any, Callable


class Tool(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def run(self, parameters: dict) -> str:
        pass

    @abstractmethod
    def get_parameters(self) -> List[ToolParameter]:
        pass


class ToolParameter(BaseModel):
    name: str
    type: str  # e.g., "string", "integer", "boolean"
    description: str
    required: bool = True
    default: Any = None

class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, Tool] = {}
        self._functions: dict[str, callable] = {}

    def register_tool(self, tool: Tool):
        if tool.name in self.tools:
            print(f"warning: tool '{tool.name}' 已存在，将被覆盖")
        self.tools[tool.name] = tool
        print(f"tool '{tool.name}' 已注册")

    def register_function(self, name: str, description: str, func: Callable[[str], str]):
        if name in self._functions:
            print(f"warning: function '{name}' 已存在，将被覆盖")
        self._functions[name] = func
        print(f"function '{name}' 已注册")
