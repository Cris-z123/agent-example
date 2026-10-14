import json
import operator
import os
import re
from dataclasses import dataclass
from typing import Annotated

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.store.postgres import PostgresStore
from typing_extensions import TypedDict

load_dotenv()


@dataclass
class Context:
    user_id: str


class ShopState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    user_profile: str


glm_llm = init_chat_model(
    model=os.getenv("GLM_MODEL_ID"),
    model_provider="openai",
    base_url=os.getenv("GLM_BASE_URL"),
    api_key=os.getenv("GLM_API_KEY"),
)


def extract_profile(state: ShopState, runtime: Runtime[Context]):
    user_id = runtime.context.user_id
    ns = (user_id, "profile")

    if runtime.store:
        items = runtime.store.search(ns)
    else:
        items = []

    if items:
        profile_parts = []
        for item in items:
            for k, v in item.value.items():
                profile_parts.append(f"{k}: {v}")
        profile_text = "; ".join(profile_parts)
        return {"user_profile": profile_text}
    else:
        return {"user_profile": ""}


def process_message(state: ShopState, runtime: Runtime[Context]):
    profile = state["user_profile"]
    user_msg = state["messages"][-1].content

    prompt = SystemMessage(
        content=(
            "你是一个用户画像分析助手。根据用户的消息，提取以下信息（如果有的话）：\n"
            "- 尺码偏好（如 M码、L码）\n"
            "- 预算范围（如 2000以内）\n"
            "- 颜色偏好（如 喜欢黑色）\n"
            "- 品牌偏好（如 喜欢Nike）\n"
            "- 品类需求（如 想买运动鞋）\n\n"
            "请以 JSON 格式输出，只包含能从消息中明确提取到的字段。"
            "如果用户没有提到某个字段，不要编造。\n"
            '示例输出: {"尺码": "M码", "预算": "2000以内", "颜色偏好": "不喜欢红色"}\n\n'
            f"用户已有画像: {profile if profile else '暂无'}"
        )
    )

    response = glm_llm.invoke([prompt, HumanMessage(content=user_msg)])
    extracted = response.content.strip()

    return {"messages": [AIMessage(content=f"[用户画像]提取：{extracted}")]}


def extract_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON 对象，兼容 ```json 代码块等包裹格式。"""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(match.group(0) if match else text)


def save_to_store(state: ShopState, runtime: Runtime[Context]):
    user_id = runtime.context.user_id
    ns = (user_id, "profile")

    last_ai_msg = state["messages"][-1].content

    if "提取：" not in last_ai_msg:
        return {"messages": [AIMessage(content="[存储]本地未提取到新的偏好信息")]}

    data = extract_json(last_ai_msg.split("提取：", 1)[-1])
    if runtime.store and data:
        profile_text = ""
        for k, v in data.items():
            profile_text += f"{k}: {v};"
            runtime.store.put(ns, f"pref_{k}", {k: v})
        return {"user_profile": profile_text, "messages": [AIMessage(content=f"[存储]已更新用户画像，更新内容：{data}")]}

    return {"messages": [AIMessage(content="[存储]本地未提取到新的偏好信息")]}


def generate_reply(state: ShopState):
    profile = state["user_profile"]

    system_content = "你是一个智能购物助手，请根据用户画像提供个性化推荐。回复控制在100字以内。"

    if profile:
        system_content += f"\n\n当前用户画像: {profile}"

    response = glm_llm.invoke([SystemMessage(content=system_content), HumanMessage(content=state["messages"][-1].content)])

    return {"messages": [AIMessage(content=response.content)]}


builder = StateGraph(state_schema=ShopState, context_schema=Context)
builder.add_node("extract_profile", extract_profile)
builder.add_node("process_message", process_message)
builder.add_node("save_to_store", save_to_store)
builder.add_node("generate_reply", generate_reply)

builder.add_edge(START, "extract_profile")
builder.add_edge("extract_profile", "process_message")
builder.add_edge("process_message", "save_to_store")
builder.add_edge("save_to_store", "generate_reply")
builder.add_edge("generate_reply", END)


if __name__ == "__main__":
    DB_URL = "postgresql://orionamesh:orionamesh@localhost:5432/langgraph_db"

    with PostgresSaver.from_conn_string(DB_URL) as checkpointer, PostgresStore.from_conn_string(DB_URL) as store:
        checkpointer.setup()
        store.setup()

        graph = builder.compile(checkpointer=checkpointer, store=store)

        # config1 = {"configurable": {"thread_id": "thread_001"}}

        # result1 = graph.invoke({"messages": [HumanMessage(content="我要买一双运动鞋, 预算1000, 我喜欢黑色和白色")]}, config1, context=Context(user_id="user_001"))

        # print("result:", result1["messages"][-1].content)

        # print("=" * 100)
        # print("当前store数据:")
        # items = store.search(("user_001", "profile"))
        # for i in items:
        #     print(f"[{i.key}]{i.value}")
        # print("=" * 100)

        config2 = {"configurable": {"thread_id": "thread_002"}}

        result2 = graph.invoke({"messages": [HumanMessage(content="我要买一双鞋，预算500")]}, config2, context=Context(user_id="user_001"))

        print("result:", result2["messages"][-1].content)

        print("=" * 100)
        print("当前store数据:")
        items = store.search(("user_001", "profile"))
        for i in items:
            print(f"[{i.key}]{i.value}")
        print("=" * 100)
