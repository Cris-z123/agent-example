import asyncio
import operator
import os
import time
from typing import Annotated

from dotenv import load_dotenv
from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.chat_models import init_chat_model
from langchain.messages import ToolMessage
from langchain.tools import tool
from langchain_mcp_adapters.callbacks import CallbackContext, Callbacks
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from mcp.shared.context import RequestContext
from mcp.types import ElicitRequestParams, ElicitResult, LoggingMessageNotificationParams
from pydantic import BaseModel

load_dotenv()


class CustomContext(BaseModel):
    user_id: str
    user_name: str


class CustomState(AgentState):
    audit_log: Annotated[list[str], operator.add]  # 当多个节点（或同一个节点多次）对该字段进行更新时，合并策略是使用 operator.add（即列表拼接）


@tool
def validate_phone(phone: str) -> str:
    """
    手机号格式校验
    Args:
        phone: 手机号
    Returns:
        校验信息
    """
    if len(phone) == 11 and phone.isdigit() and phone.startswith("1"):
        return f"手机号 {phone} 格式正确"
    return f"手机号 {phone} 格式错误，应为 11 位数字且以 1 开头"


# 工具拦截器：认证注入
async def auth_inject(request: MCPToolCallRequest, handler):
    """将用户身份注入 MCP 工具参数"""
    ctx: CustomContext = request.runtime.context
    return await handler(request.override(args={**request.args, "caller_id": f"{ctx.user_id}({ctx.user_name})"}))


async def audit_log(request: MCPToolCallRequest, handler):
    runtime = request.runtime
    result = await handler(request)

    text = result.content[0].text if result.content else ""

    tool_msg = ToolMessage(content=text, tool_call_id=runtime.tool_call_id)

    log_entry = f"[{time.strftime('%H:%M:%S')}] {runtime.context.user_name} -> {request.name}: {str(request.args)}"

    return Command(update={"messages": [tool_msg], "audit_log": [log_entry]})


def on_progress(progress, total, message, context: CallbackContext):
    if total:
        pct = progress / total * 100
        print(f" [进度] {progress}/{total} ({pct:.0f}%) - {message or ''}")


def on_logging(params: LoggingMessageNotificationParams, context):
    msg = params.data.get("msg")
    print(f" [{context.server_name}] [{params.level}] {msg}")


def on_elicitation(mcp_context: RequestContext, params: ElicitRequestParams, context: CallbackContext) -> ElicitResult:
    """大额退款时，让用户在控制台确认"""
    print(f"{'=' * 50}")
    print(f" [系统询问] {params.message}")

    schema = params.requestedSchema
    options = schema["properties"]["value"]["enum"]

    if options:
        for i, opt in enumerate(options, 1):
            print(f" {i}. {opt}")

        while True:
            choice = input(f" 请输入选项编号 (1-{len(options)}): ").strip()

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    selected = options[idx]
                    break
            except ValueError:
                pass
            print(f" 输入无效，请输入 1 到 {len(options)} 之间的数字")

        print(f" 你选择了: {selected}")
    else:
        selected = input(" 请输入: ").strip()

    print(f"{'=' * 50}")

    return ElicitResult(action="accept", content={"value": selected})


async def handle_interrupts(result, agent, config, context):
    while result.interrupts:
        interrupt_data = result.interrupts[0].value
        action_requests = interrupt_data["action_requests"]
        review_configs = interrupt_data["review_configs"]

        for i, req in enumerate(action_requests):
            cfg = review_configs[i]
            print(f"\n [{i}] 工具名称 : {req['name']}")
            print(f" 参数 : {req['args']}")
            print(f" 允许决策 : {cfg['allowed_decisions']}")

        decisions = []

        print(f"\n{'·' * 40}")
        print("请按顺序对以上操作做出决策：")
        print(f"{'·' * 40}")

        for i, req in enumerate(action_requests):
            allowed = review_configs[i]["allow_decisions"]

            if req.get("args"):
                for k, v in req["args"].items():
                    print(f" 参数: {k} = {v}")

            hint_map = {
                "approve": "批准，按原参数执行工具",
                "edit": "修改参数后执行工具",
                "reject": "拒绝执行，附带反馈说明",
                "respond": "跳过工具执行，直接返回人工回复",
            }

            for a in allowed:
                print(f" > {a} — {hint_map.get(a)}")

            while True:
                decision = input(f" >>> 输入操作 ({'/'.join(allowed)}): ").strip().lower()
                if decision in allowed:
                    break
                print(f" 无效输入，该操作只允许: {allowed}")

            if decision == "approve":
                decisions.append({"type": "approve"})
                print(" 已批准 —— 工具将按原参数执行")
            elif decision == "edit":
                print(" 请输入修改后的参数（直接回车保留原值）：")
                new_args = {}
                for k, v in req["args"].items():
                    new_val = input(f" {k} [原值: {str(v)}]: ").strip()
                    if new_val == "":
                        new_args[k] = v
                    else:
                        new_args[k] = new_val
                    decisions.append(
                        {
                            "type": "edit",
                            "edited_action": {"name": req["name"], "args": new_args},
                        }
                    )
                    print(f" 已修改参数: {new_args}")
            elif decision == "reject":
                reason = input(" 请输入拒绝原因: ").strip()
                if not reason:
                    reason = "操作被人工拒绝"
                    decisions.append({"type": "reject", "message": reason})
                    print(f" 已拒绝: {reason}")
            elif decision == "respond":
                reply = input(" 请输入回复内容: ").strip()
                if not reply:
                    reply = "已确认，没有补充信息。"
                    decisions.append({"type": "respond", "message": reply})
                    print(f" 已回复: {reply}")

        print(f"\n{'─' * 60}")
        print(f"提交决策列表: {decisions}")
        print(f"{'─' * 60}")

        result = await agent.ainvoke(
            Command(resume={"decisions": decisions}),
            config=config,
            context=context,
            version="v2",
        )

    return result


async def main():
    client = MultiServerMCPClient(
        {
            "order_server": {
                "transport": "http",
                "url": "http://localhost:8001/order",
            },
            "notify_server": {
                "transport": "http",
                "url": "http://localhost:8002/notify",
            },
        },
        tool_interceptors=[auth_inject, audit_log],
        callbacks=Callbacks(
            on_progress=on_progress,
            on_logging_message=on_logging,
            on_elicitation=on_elicitation,
        ),
    )

    mcp_tools = await client.get_tools()

    blobs = await client.get_resources("notify_server", uris=["company://policies/return"])
    policy_text = "/n".join(b.as_string() for b in blobs)

    msgs = await client.get_prompt("notify_server", "refund_response", arguments={"order_id": "{订单号}", "amount": "{金额}"})

    prompt_template = msgs[0].content if msgs else ""

    all_tools = mcp_tools + [validate_phone]

    checkpointer = MemorySaver()

    glm_llm = init_chat_model(
        model=os.getenv("GLM_MODEL_ID"),
        model_provider="openai",
        base_url=os.getenv("GLM_BASE_URL"),
        api_key=os.getenv("GLM_API_KEY"),
    )

    agent = create_agent(
        model=glm_llm,
        tools=all_tools,
        context_schema=CustomContext,
        state_schema=CustomState,
        checkpointer=checkpointer,
        middleware=[
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "process_refund": {
                        "allowed_decisions": ["approve", "reject"],
                        "description": "退款操作需要人工审批，请确认是否执行退款",
                    }
                }
            )
        ],
        system_prompt=f"""
            你是电商售后客服助手。
            工作流程： 1. 查询订单时调用 query_order。如果订单不存在，直接告知用户不要重试。
            2. 退款时先查询订单确认状态和金额。
            3. 退款成功后询问用户是否需要短信通知。如果要通知，先调用 validate_phone 校验手机号，再用 send_sms 发送。
            4. 涉及退换货政策问题时，参考以下政策： {policy_text}
            5. 回复退款结果时，参考以下模板： {prompt_template}
        """,
    )

    ctx = CustomContext(user_id="user_123", user_name="123")

    config = {"configurable": {"thread_id": "session_01"}}

    print("=" * 60)
    print(" 电商智能售后系统")
    print(" 输入 'quit' / 'exit' / '退出' 结束对话")
    print("=" * 60)

    while True:
        try:
            user_input = input("[你]: ").strip()

            if user_input.lower() in ("quit", "exit", "退出", "q"):
                print("再见！")
                break
            if not user_input:
                continue

            result = await agent.ainvoke({"messages": {"role": "user", "content": user_input}}, config=config, context=ctx, version="v2")

            result = await handle_interrupts(result, agent, config, ctx)

            final_msg = result.value["messages"][-1]
            print(f"[助手]: {final_msg.content}")

            audit = result.value.get("audit_log", [])

            if audit:
                print("审计日志:")
                for entry in audit:
                    print(f" {entry}")

        except Exception as e:
            print(f"错误：{e}")


if __name__ == "__main__":
    asyncio.run(main())
