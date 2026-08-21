
import uuid

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware, wrap_tool_call
from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime, tool
from langgraph.checkpoint.mysql.pymysql import PyMySQLSaver
from langgraph.store.mysql.pymysql import PyMySQLStore
from langgraph.types import Command
from pydantic import BaseModel, Field

load_dotenv()

class UserContext(BaseModel):
    user_id: str = Field(description="用户唯一标识")
    channel: str = Field(description="用户访问渠道")

class CustomerSessionState(BaseModel):
    current_order_id: str = Field(default=None, description="当前用户查询的订单号")

MOCK_DATABASE = {
    "orders": {
        "order001": {
            "order_id": "order001", "status": "已发货", "product": "智能手机", "preference_context": "华为手机P70"
        },
        "order002": {
            "order_id": "order002", "status": "待支付", "product": "智能手表", "preference_context": "Apple Watch Series 8"
        },
    }
}

@tool
def get_user_info(runtime: ToolRuntime) -> str:
    """
    获取用户信息
    Args:
        runtime(ToolRuntime): 包含上下文信息的运行时环境
    Returns:
        str: 当前用户信息
    """
    current_user_id = runtime.context.user_id

    user_channel = runtime.context.channel

    state = runtime.state
    if "current_order_id" in state:
        current_order_id = state["current_order_id"]
    else:
        current_order_id = "无"
    return f"用户ID: {current_user_id}, 咨询渠道: {user_channel}, 当前查询订单号: {current_order_id}"


@tool
def query_order_status(order_id: str,runtime: ToolRuntime) -> Command:
    """
    获取用户订单状态
    Args:
        order_id (str): 订单号
        runtime (ToolRuntime): 包含上下文信息的运行时环境
    Returns:
        Command: 包含更新操作的命令对象：状态中更新当前订单ID，并返回订单信息
    """
    order_info = MOCK_DATABASE["orders"].get(order_id)

    if not order_info:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"错误: 订单{order_id}不存在。",
                        tool_call_id=runtime.tool_call_id
                    )
                ]
            }
        )

    updates = {
        "current_order_id": order_id,
        "messages": [
            ToolMessage(
                content=f"订单号: {order_info['order_id']}, 状态: {order_info['status']}, 产品: {order_info['product']}"
                        f"需要更新用户偏好，用户偏好: {order_info['preference_context']}",
                tool_call_id=runtime.tool_call_id
            )
        ]
    }
    return Command(update=updates)

@tool
def update_user_preference(category: str, liked_item: str, runtime: ToolRuntime) -> str:
    """
    更新用户偏好
    Args:
        category (str): 偏好类别
        liked_item (str): 用户喜欢的物品
        runtime (ToolRuntime): 包含上下文信息的运行时环境
    Returns:
        str: 更新结果信息
    """
    user_id = runtime.context.user_id
    namespace = (f"user_{user_id}", "preferences")

    key = str(uuid.uuid4())

    value_to_store = {
        "category": category,
        "liked_item": liked_item
    }

    runtime.store.put(namespace, key, value_to_store)
    return f"已更新用户偏好到longTermMemory: 类别 - {category}, 喜欢的物品 - {liked_item}"


def get_recommendation(runtime: ToolRuntime) -> str:
    """
    根据用户偏好推荐商品
    Args:
        runtime (ToolRuntime): 包含上下文信息的运行时环境
    Returns:
        str: 推荐商品信息的字符串
    """
    user_id = runtime.context.user_id
    current_order = runtime.state.get("current_order_id", "未知订单")
    namespace = (f"user_{user_id}", "preferences")
    prefs = runtime.store.search(namespace)

    pref_list = []

    if prefs:
        for p in prefs[-3:]:
            pref_list.append(f"{p.value_get('category')}: {p.value_get('liked_item')}")

    return f"根据用户当前订单[{current_order}]和长期偏好{pref_list if pref_list else '无'}, 为用户推荐相关配件或类型风格商品"

@wrap_tool_call
def handle_tool_errors(request, handler):
    try:
        return handler(request)
    except Exception as e:
        return ToolMessage(
            content=f"调用工具错误: 请稍后重试，错误信息: ({str(e)})",
            tool_call_id=request.tool_call["id"]
        )


DB_URL = "mysql+pymysql://root:root@localhost:3306/langchain_db?charset=utf8mb4"

with(
    PyMySQLSaver.from_conn_string(DB_URL) as checkpointer,
    PyMySQLStore.from_conn_string(DB_URL) as store
):
    checkpointer.setup()
    store.setup()

    agent = create_agent(
        model=glm_llm,
        tools=[get_user_info, query_order_status, update_user_preference, get_recommendation],
        system_prompt="""
                    你是一个智能电商客服助手，具备回答用户咨询、获取用户信息、查询订单状态、更新用户偏好和推荐商品功能。"
                    获取用户信息请调用 get_user_info 工具。
                    查询订单状态请调用 query_order_status 工具，查询到订单状态后，还需要调用 update_user_preference 工具更新用户偏好。
                    更新用户偏好请调用 update_user_preference 工具。
                    获取推荐商品请调用 get_recommendation 工具。
        """,
        checkpointer=checkpointer,
        store=store,
        state_schema=CustomerSessionState,
        context_schema=UserContext,
        middleware=[
            SummarizationMiddleware(
                model=glm_llm,
                summary_prompt="请总结以下对话内容：{messages}",
                trigger=("messages", 10),
                keep=("messages", 5)
            ),
            handle_tool_errors
        ]
    )

    # 控制台交互循环 (流式调用) — 必须在 with 块内，保证 checkpointer/store 的连接存活
    print("=" * 50)
    print("智能电商客服助手")
    print("功能: 查询订单、更新偏好、获取推荐。")
    print("输入 'quit' 或 '退出' 结束对话。")
    print("=" * 50)

    user_context = UserContext(user_id="user_001", channel="web")

    config = {"configurable": {"thread_id": "session_01"}}

    while True:
        try:
            user_input = input("[你]: ").strip()

            if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                print('客服助手: 下次再见!')
                break

            if not user_input:
                continue

            input_data = {"messages": {"role": "user", "content": user_input}}

            print("[客服助手]: ")

            for chunk in agent.stream(input_data, config=config, context=user_context):
                for step, data in chunk.items():
                    if step in ["model", "tools"]:
                        message = data["messages"][-1]
                        message.pretty_print()
        except Exception as e:
            print(f"调用过程出现错误: {e}")
