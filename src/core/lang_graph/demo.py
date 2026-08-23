import operator
import os
from typing import Annotated, Literal

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.messages import AnyMessage, SystemMessage
from langchain.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

load_dotenv()


# 1. 定义工具
@tool
def add(a: int, b: int) -> int:
    """两个整数相加。
    Args:
        a: 第一个整数
        b: 第二个整数
    Return
        结果
    """
    return a + b


@tool
def multiply(a: int, b: int) -> int:
    """
    两个整数相乘。
    Args:
        a: 第一个整数
        b: 第二个整数
    Return
        结果
    """
    return a * b


@tool
def divide(a: int, b: int) -> float:
    """两个整数相除。
    Args:
        a: 第一个整数
        b: 第二个整数
    Return
        结果
    """
    return a / b


glm_llm = init_chat_model(
    model=os.getenv("GLM_MODEL_ID"),
    model_provider="openai",
    base_url=os.getenv("GLM_BASE_URL"),
    api_key=os.getenv("GLM_API_KEY"),
)

# 工具列表和工具名索引
tools = [add, multiply, divide]
# 工具名索引，用于根据工具名快速查找工具
tools_by_name = {t.name: t for t in tools}
model_with_tools = glm_llm.bind_tools(tools)


# 2. 定义状态
class CalculatorState(TypedDict):
    """计算器 Agent 的状态，消息列表使用 operator.add 做追加合并"""

    messages: Annotated[list[AnyMessage], operator.add]


# 3. 定义节点
def llm_call(state: CalculatorState) -> dict:
    """LLM 节点：调用模型，决定是调用工具还是直接回答"""
    response = model_with_tools.invoke([SystemMessage(content="你是一个数学计算助手。请使用工具完成计算并给出最终答案。")] + state["messages"])
    return {"messages": [response]}


# 4. 路由逻辑（条件边）
def should_continue(state: CalculatorState) -> Literal["tool_node", END]:
    """检查最后一条消息，如果有 tool_calls 则进入工具节点，否则结束"""
    last_message = state["messages"][-1]
    # 检查是否有 tool_calls 且 tool_calls 不为空
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_node"
    return END


# 5. 构建和编译图
builder = StateGraph(CalculatorState)
builder.add_node("llm_call", llm_call)
builder.add_node("tool_node", ToolNode(tools))

builder.add_edge(START, "llm_call")
builder.add_conditional_edges("llm_call", should_continue, ["tool_node", END])
builder.add_edge("tool_node", "llm_call")

graph = builder.compile()
