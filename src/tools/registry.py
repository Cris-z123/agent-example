import time
from typing import Any, Callable, Dict, Optional

from tools.tools import Tool


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

    def register_function(self, func: Callable, name: Optional[str] = None, description: Optional[str] = None):
        if name is None:
            name = func.__name__

        if description is None:
            import inspect
            doc = inspect.getdoc(func)
            if doc:
                description = doc.split("\n")[0].strip()
            else:
                description = f"执行 {name}"
        if name in self._functions:
            print(f"warning: function '{name}' 已存在，将被覆盖")

        self._functions[name] = {
            "description": description,
            "func": func
        }
        print(f"function '{name}' 已注册")

    def unregister(self, name: str):
        if name in self._tools:
            del self._tools[name]
            print(f"tool '{name}' 已注销")
        elif name in self._functions:
            del self._functions[name]
            print(f"function '{name}' 已注销")
        else:
            print(f"warning: '{name}' 不存在于工具注册表中")

    def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def get_function(self, name: str) -> Optional[Callable]:
        func_info = self._functions.get(name)
        if func_info:
            return func_info["func"]
        return None

    def excute_tool(self, name:str, input_text: str) -> ToolResponse:
        if self.circuit_breaker.is_open(name):
            status = self.circuit_breaker.get_status(name)
            return ToolResponse.error(
                code =ToolErrorCode.CIRCUIT_OPEN,
                message = f"工具 '{name}' 当前被禁，由于连续失败，暂时无法使用 ({status['recover_in_seconds']}秒后尝试恢复)",
                context={
                    "tool_name": name,
                    "circuit_status": status
                }
            )
        response = None

        if name in self._tools:
            tool = self._tools[name]
            try:
                import json
                if isinstance(input_text, str):
                    try:
                        parameters = json.loads(input_text)
                    except json.JSONDecodeError:
                        parameters = {"input": input_text}
                elif isinstance(input_text, dict):
                    parameters = input_text
                else:
                    parameters = {"input": str(input_text)}

                response = tool.run_with_timing(parameters)
            except Exception as e:
                return ToolResponse.error(
                    code=ToolErrorCode.EXECUTION_ERROR,
                    message=f"执行工具 '{name}' 时发生错误: {str(e)}",
                    context={
                        "tool_name": name,
                        "input": input_text,
                    }
                )
        elif name in self._functions:
            func = self._functions[name]["func"]
            start_time = time.time()
            try:
                result = func(input_text)
                elapsed_time = int((time.time() - start_time) * 1000)
                response = ToolResponse.success(
                    text=str(result),
                    data=('output', result),
                    stats={'time_ms': elapsed_time},
                    context={"tool_name": name, "input": input_text}
                )
            except Exception as e:
                elapsed_time = int((time.time() - start_time) * 1000)
                return ToolResponse.error(
                    code=ToolErrorCode.EXECUTION_ERROR,
                    message=f"执行函数 '{name}' 时发生错误: {str(e)}",
                    stats={'time_ms': elapsed_time},
                    context={
                        "function_name": name,
                        "input": input_text,
                    }
                )

        else:
            response = ToolResponse.error(
                code=ToolErrorCode.NOT_FOUND,
                message=f"工具或函数 '{name}' 未找到",
                context={"tool_name": name}
            )

        self.circuit_breaker.record_result(name, response)

        return response
