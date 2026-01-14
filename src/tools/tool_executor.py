from typing import Dict, Any

class ToolExecutor:
    """
    工具执行器，负责管理和执行工具。
    """
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}

    def registerTool(self, name: str, description: str, func: callable):
        if name in self.tools:
            print(f"warning: tool '{name}' 已存在，将被覆盖")
        self.tools[name] = {"description": description, "func": func}
        print(f"tool '{name}' 已注册")
    
    def getTool(self, name: str) -> callable:
        return self.tools.get(name, {}).get("func")
    
    def getAvailableTools(self) -> str:
        return "\n".jon([
            f"- {name}: {info['description']}"
            for name, info in self.tools.items()
        ])
