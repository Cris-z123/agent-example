from typing import Dict, Any

# 尝试相对导入；如果脚本直接运行（没有父包），回退到在运行时添加 src 到 sys.path 再做绝对导入
try:
    from .get_weather import get_weather
except Exception:
    import sys
    import os
    current_dir = os.path.dirname(__file__)
    src_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    from tools.get_weather import get_weather

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
        return "\n".join([
            f"- {name}: {info['description']}"
            for name, info in self.tools.items()
        ])

# --- 工具初始化与使用示例 ---
if __name__ == '__main__':
    # 1. 初始化工具执行器
    toolExecutor = ToolExecutor()

    # 2. 注册我们的实战搜索工具
    tool_description = "一个天气查询工具。当你需要回答某个地区的天气时，应使用此工具。"
    # 使用小写注册名以和其它模块（如 tool_definitions）保持一致
    toolExecutor.registerTool("get_weather", tool_description, get_weather)

    # 3. 打印可用的工具
    print("\n--- 可用的工具 ---")
    print(toolExecutor.getAvailableTools())

    # 4. 智能体的Action调用示例：传入城市名称
    print("--- 执行 Action: get_weather['广州'] ---")
    tool_name = "get_weather"
    tool_input = "广州"

    tool_function = toolExecutor.getTool(tool_name)
    if tool_function:
        observation = tool_function(tool_input)
        print("--- 观察 (Observation) ---")
        print(observation)
    else:
        print(f"错误:未找到名为 '{tool_name}' 的工具。")