from typing import Any, Dict, Optional


class ToolRegistry:
    def __init__(self, circuit_breaker: Optional[CircuitBreaker] = None):
        self._tools: dict[str, Tool] = {}
        self._functions: dict[str, dict[str, Any]] = {}

        self.readmeta_cache: Dict[str, Dict[str, Any]] = {}
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

    def register_tool(self, tool: Tool, auto_expand: bool = True):
        if auto_expand and hasattr(tool, "expand_tools") and tool.expandable:
            expanded_tools = tool.get_expanded_tools()
            if expanded_tools:
                for sub_tool in expanded_tools:
                    if sub_tool.name in self._tools:
                        print(f"warning: tool '{sub_tool.name}' 已存在，将被覆盖")
                    self._tools[sub_tool.name] = sub_tool
                print(f"tool '{tool.name}' 已自动展开为 {len(expanded_tools)} 个子工具")
                return

        if tool.name in self._tools:
            print(f"warning: tool '{tool.name}' 已存在，将被覆盖")

        self._tools[tool.name] = tool
        print(f"tool '{tool.name}' 已注册")
