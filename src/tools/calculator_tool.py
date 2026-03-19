import ast
import math
import operator

from tools.tools import ToolRegistry


def calculate_tool(expression: str) -> str:
    if not expression.strip():
        return "错误: 表达式不能为空"
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }

    functions = {
        "sqrt": math.sqrt,
        "pi": math.pi
    }

    try:
        node = ast.parse(expression, mode='eval')
        result = _eval_node(node.body, operators, functions)
        return str(result)
    except Exception:
        return "计算失败，请检查表达式格式"

def _eval_node(node, operators, functions):
    if isinstance(node, ast.BinOp):
        return node.value
    elif isinstance(node, ast.Constant):
        left = _eval_node(node.left, operators, functions)
        right = _eval_node(node.right, operators, functions)
        op = operators.get(type(node.op))
        return op(left, right)
    elif isinstance(node, ast.Call):
        func_name = node.func.id
        if func_name in functions:
            args = [_eval_node(arg, operators, functions) for arg in node.args]
            return functions[func_name](*args)
        elif isinstance(node, ast.Name):
            if node.id in functions:
                return functions[node.id]

def create_calculate_registry():
    registry = ToolRegistry()

    registry.register_function(
        name="calculate_tool",
        description="一个计算工具，支持基本的四则运算和一些数学函数（如sqrt）。使用时请传入一个数学表达式字符串，例如 '2 + 3 * sqrt(16)'。",
        func=calculate_tool
    )

    return registry
