from .get_weather import get_weather

"""
工具定义模块
此模块集中定义所有可用的工具, 并导出为 `tool_definitions` 映射
"""

# 工具函数映射，用于根据函数名调用对应的函数
tool_definitions = {"get_weather": get_weather}
