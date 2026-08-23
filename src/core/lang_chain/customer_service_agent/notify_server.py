from fastmcp import FastMCP

mcp = FastMCP("通知服务")


@mcp.tool()
async def send_sms(phone: str, content: str, caller_id: str = "") -> str:
    """
    向指定手机号发送短信通知。caller_id 由系统自动注入。
    Args:
        phone: 手机号
        content: 短信内容
        caller_id: 操作人ID，默认为空字符串
    Returns:
        短信发送结果字符串
    """
    return f"短信已发送：号码={phone}，内容='{content}'操作人: {caller_id}"


@mcp.resource("company://policies/return", mime_type="text/markdown", description="退换货政策")
def get_return_policy() -> str:
    return """
        ## 退换货政策 1. 签收后 7 天内可无理由退货（商品不影响二次销售）
        # 2. 质量问题 30 天内可换货，运费商家承担
        # 3. 退货时赠品需一并退回
        # 4. 退款将在收货确认后 3 个工作日内退回原支付方式
    """


@mcp.prompt
def refund_response(order_id: str, amount: str) -> str:
    return f"好的，已为您处理订单 {order_id} 的退款。\n退款金额：{amount} 元\n预计 3 个工作日内退回原支付方式。\n如有疑问可随时联系我们。"


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8002, path="/notify")
