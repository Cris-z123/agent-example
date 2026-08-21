from fastmcp import FastMCP

mcp = FastMCP("Weather")

# 工具可以异步也可以同步
@mcp.tool()
async def get_weather(location: str) -> str:
    """
    获取指定城市的天气信息
    Args:
        location: str
    Returns:
        天气信息
    """
    weather_data = {
        "北京": "晴，22~28°C，北风3级",
        "上海": "多云，25~30°C，东南风2级",
        "深圳": "阵雨，26~31°C，南风4级",
    }

    return weather_data.get(location, "暂未找到")


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8001,
        path="/test"
    )
