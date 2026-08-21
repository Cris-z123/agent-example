import asyncio

from fastmcp import Context, FastMCP

mcp = FastMCP(
    "订单服务"
)

ORDERS = {
    "ORD-001": {"product": "无线耳机", "status": "已签收", "amount": 299.0},
    "ORD-002": {"product": "机械键盘", "status": "已签收", "amount": 500.0},
    "ORD-003": {"product": "4K显示器", "status": "已签收", "amount": 2499.0},
    "ORD-004": {"product": "鼠标垫", "status": "配送中", "amount": 29.0},
}

@mcp.tool()
async def query_order(order_id: str, caller_id: str = "", ctx: Context = None) -> str:
    """
    查询订单信息
    Args:
        order_id: 订单ID
        caller_id: 调用者ID
        ctx: mcp上下文
    Returns:
        str: 订单信息
    """
    await ctx.info(f"开始查询订单信息, 订单id{order_id}")

    order = ORDERS.get(order_id)

    if order:
        return (
            f"订单ID: {order_id}\n"
            f"产品: {order['product']}\n"
            f"状态: {order['status']}\n"
            f"金额: {order['amount']}\n"
            f"调用者ID: {caller_id}\n"
        )
    else:
        return f"订单ID: {order_id}\n订单不存在, 调用者ID: {caller_id}\n"

@mcp.tool()
async def process_refund(order_id: str, reason: str, caller_id: str = "", ctx: Context = None) -> str:
    """
    处理退款请求
    Args:
        order_id: 订单ID
        reason: 退款原因
        caller_id: 调用者ID
        ctx: mcp上下文
    Returns:
        str: 退款结果
    """

    await ctx.info(f"开始处理退款请求, 订单id{order_id}, 退款原因{reason}, 调用者id{caller_id}")

    order = ORDERS.get(order_id)

    if not order:
        return f"订单ID: {order_id}\n订单不存在, 调用者ID: {caller_id}\n"

    amount = order['amount']

    if amount >= 500:
        result = await ctx.elicit(
            message=f"订单金额{amount}, 退款原因{reason}, 调用者id{caller_id}, 是否确认退款?",
            response_type=["确认", "取消"],
        )

        if result.action == "decline":
            ctx.info(f"订单{order_id}, 用户拒绝退款")
            return "用户拒接退款"
        elif result.action == "cancel":
            ctx.info(f"订单{order_id}, 用户取消退款")
            return "用户退款取消"
        else:
            ctx.info(f"订单{order_id}, 用户确认退款")
            ORDERS[order_id]["status"] = "已退款"
            return f"用户确认退款，退款金额：{amount}, 退款原因：{reason}, 调用者ID: {caller_id}, 已成功退款， 订单状态已更新为已退款"

    else:
        ORDERS[order_id]["status"] = "已退款"
        return f"订单ID: {order_id}\n订单金额小于500, 直接退款, 调用者ID: {caller_id}\n"


@mcp.tool()
async def batch_refund(order_ids: str, reason: str, caller_id: str= "", ctx: Context = None):
    """
    批量处理退款请求
    Args:
        order_ids: 订单ID
        reason: 退款原因
        caller_id: 调用者ID
        ctx: mcp上下文
    Returns:
        str: 退款结果
    """

    await ctx.info(f"开始批量处理退款请求, 订单id{order_ids}, 退款原因{reason}, 调用者id{caller_id}")

    ids = [i.strip() for i in order_ids.split(",") if i.strip()]

    total_count = len(ids)
    success_count = 0

    for i, order_id in enumerate(ids):
        await asyncio.sleep(1)

        order = ORDERS.get(order_id)
        if order and order["status"] == "已签收" and order["amount"] < 500:
            ORDERS[order_id]["status"] = "已退款"
            success_count += 1
            await ctx.info("订单{order_id}退款成功, 调用者id{caller_id}")
        else:
            ctx.info(f"订单{order_id}退款失败, 调用者id{caller_id}")

        ctx.report_progress(i, total_count, f"退款进度{i}/{total_count}")

    await ctx.info(f"批量退款处理完成, {success_count}/{total_count}")

    return f"批量处理订单退款完成, 订单id{order_ids}, 退款成功:{success_count}, 退款失败:{total_count - success_count}, 调用者id{caller_id}"

if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8001,
        path="/order"
    )
