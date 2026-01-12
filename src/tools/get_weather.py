import json

import requests


def get_weather(city: str) -> str:
    """
    通过城市名称获取天气信息

    :param city: 城市名称
    :return: 天气信息
    :rtype: str
    """

    url = f"http://wttr.in/{city}?format=j1"

    try:
        response = requests.get(url)
        response.raise_for_status()
        weather_data = response.json()

        current_condition = weather_data["current_condition"][0]
        temp_C = current_condition["temp_C"]
        weather_desc = current_condition["weatherDesc"][0]["value"]

        return f"{city}当前天气: {weather_desc}气温: {temp_C}°C"

    except requests.RequestException as e:
        return f"获取天气信息失败: {e}"
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return f"解析天气信息失败: {e}"
