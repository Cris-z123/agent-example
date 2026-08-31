from __future__ import annotations

from abc import ABC, abstractmethod
from ast import List
from typing import Any, Callable, Dict

from pydantic import BaseModel


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
        self._functions: dict[str, dict[str, Any]] = {}

    def register_tool(self, tool: Tool):
        if tool.name in self.tools:
            print(f"warning: tool '{tool.name}' 已存在，将被覆盖")
        self._tools[tool.name] = tool
        print(f"tool '{tool.name}' 已注册")

    def register_function(self, name: str, description: str, func: Callable[[str], str]):
        if name in self._functions:
            print(f"warning: function '{name}' 已存在，将被覆盖")
        self._functions[name] = {
            "description": description,
            "func": func
        }
        print(f"function '{name}' 已注册")

    def get_tools_description(self) -> str:

        descriptions = []

        for tool in self._tools.values():
            descriptions.append(f"-{tool.name}: {tool.description}")

        for name, info in self._functions.items():
            descriptions.append(f"-{name}: {info['description']}")

        return "\n".join(descriptions) if descriptions else "暂无可用工具"

    def to_openai_schema(self) -> Dict[str, Any]:
        parameters = self.get_parameters()

        properties = {}

        required = []

        for param in parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }

            if param.default is not None:
                prop["description"] = f"{param.description} (默认: {param.default})"

            if param.type == "array":
                prop["items"] = {"type": "string"}

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "type": self.name,
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
