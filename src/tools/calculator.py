import math
from typing import Any


def calculate(expression: str) -> str:
    """
    计算数学表达式。

    支持基本的数学运算（+、-、*、/、**、%等）和常用数学函数（sin、cos、sqrt等）。
    表达式会被安全地评估，只允许数学运算。

    Args:
        expression: 要计算的数学表达式字符串

    Returns:
        计算结果字符串，如果计算失败则返回错误信息

    Examples:
        >>> calculate("2 + 3")
        '5'
        >>> calculate("sqrt(16)")
        '4.0'
        >>> calculate("sin(pi/2)")
        '1.0'
    """
    # 创建安全的命名空间，只包含数学函数和常量
    safe_dict: dict[str, Any] = {
        "__builtins__": {},
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        # 数学常量
        "pi": math.pi,
        "e": math.e,
        "tau": math.tau,
        # 数学函数
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "atan2": math.atan2,
        "sinh": math.sinh,
        "cosh": math.cosh,
        "tanh": math.tanh,
        "asinh": math.asinh,
        "acosh": math.acosh,
        "atanh": math.atanh,
        "sqrt": math.sqrt,
        "exp": math.exp,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "ceil": math.ceil,
        "floor": math.floor,
        "fabs": math.fabs,
        "factorial": math.factorial,
        "gcd": math.gcd,
        "degrees": math.degrees,
        "radians": math.radians,
    }

    try:
        # 清理表达式，移除可能的空白字符
        expression = expression.strip()

        # 评估表达式
        result = eval(expression, safe_dict, {})

        # 格式化结果
        if isinstance(result, float):
            # 如果是整数形式的浮点数，返回整数
            if result.is_integer():
                return str(int(result))
            # 否则保留适当的小数位数
            return str(round(result, 10))
        elif isinstance(result, complex):
            return f"{result.real}+{result.imag}j"
        else:
            return str(result)

    except ZeroDivisionError:
        return "错误: 除以零"
    except ValueError as e:
        return f"错误: 无效的数学运算 - {str(e)}"
    except TypeError as e:
        return f"错误: 类型错误 - {str(e)}"
    except NameError as e:
        return f"错误: 未定义的变量或函数 - {str(e)}"
    except SyntaxError as e:
        return f"错误: 表达式语法错误 - {str(e)}"
    except Exception as e:
        return f"错误: 计算失败 - {str(e)}"
