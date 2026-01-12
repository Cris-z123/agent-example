import os
import re

from dotenv import load_dotenv

from core import OpenAICompatibleClient
from tools import tool_definitions

load_dotenv()

API_KEY = os.getenv("ALICS_API_KEY")
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_ID = "qwen-plus"

AGENT_SYSTEM_PROMPT = """
你是一个智能旅行助手。你的任务是分析用户的请求，并使用可用工具一步步地解决问题，规划用户的旅行计划并给出推荐的旅游景点。

# 可用工具:
- `get_weather(city: str)`: 查询指定城市的实时天气。

# 行动格式:
你的回答必须严格遵循以下格式。首先是你的思考过程，然后是你要执行的具体行动，每次回复只输出一对Thought-Action：
Thought: [这里是你的思考过程和下一步计划]
Action: [这里是你要调用的工具，格式为 function_name(arg_name="arg_value")]

# 任务完成:
当你收集到足够的信息，能够回答用户的最终问题时，你必须在`Action:`字段后使用 `finish(answer="...")` 来输出最终答案。

请开始吧！
"""

llm = OpenAICompatibleClient(
    model=MODEL_ID,
    api_key=API_KEY,
    base_url=BASE_URL,
    extra_body={"enable_search": True},
)

user_prompt = "我想去广州旅游"
prompt_history = [f"用户请求： {user_prompt}"]

print(f"用户输入: {user_prompt}" + "\n" + "=" * 40)

for i in range(5):
    print(f"=== 第 {i+1} 轮交互 ===")

    full_prompt = "\n".join(prompt_history)

    llm_output = llm.generate(
        prompt=full_prompt,
        system_prompt=AGENT_SYSTEM_PROMPT,
        extra_body={"enable_search": True},
    )

    match = re.search(
        r"(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)",
        llm_output,
        re.DOTALL,
    )

    if match:
        truncated = match.group(1).strip()
        if truncated != llm_output.strip():
            llm_output = truncated
            print("截断多余的Thought和Action对")
    print(f"model output: \n{llm_output}\n")
    prompt_history.append(llm_output)

    action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)

    if not action_match:
        print("parse error: 模型输出中未找到Action")
        break
    action_str = action_match.group(1).strip()

    if action_str.startswith("finish"):
        finish_match = re.search(r'finish\(answer="(.*)"\)', action_str)
        if finish_match:
            final_answer = finish_match.group(1)
            print(f"{final_answer}")
        else:
            print("parse error: finish 的格式不正确，未找到 answer")
        break

    call_match = re.search(r"^(\w+)\((.*)\)\s*$", action_str, re.DOTALL)
    if not call_match:
        print(f"parse error: Action 格式不正确: {action_str}")
        break

    tool_name = call_match.group(1)
    args_str = call_match.group(2)
    kwargs = dict(re.findall(r'(\w+)\s*=\s*"([^"]*)"', args_str))

    if tool_name in tool_definitions:
        observation = tool_definitions[tool_name](**kwargs)
    else:
        observation = f"error: 未找到工具 {tool_name}"

    observation_str = f"Observation: {observation}"
    print(f"{observation_str}\n" + "=" * 40)
    prompt_history.append(observation_str)
