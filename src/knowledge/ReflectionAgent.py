import os
import re
import sys
from enum import Enum
from typing import Any, Dict, List, Optional

if __package__ is None:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import GeneralLLMClient


class ReflectionDimension(str, Enum):
    """反思维度枚举。"""

    PERFORMANCE = "performance"
    FORMAT = "format"
    SECURITY = "security"
    BEST_PRACTICES = "best_practices"
    LOGIC_ERRORS = "logic_errors"
    SYNTAX_ERRORS = "syntax_errors"


class SupportedLanguage(str, Enum):
    """支持的语言枚举。"""

    PYTHON = "python"
    JAVA = "java"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"


# 语言检测模式
LANGUAGE_PATTERNS: Dict[str, List[str]] = {
    SupportedLanguage.PYTHON: [
        r"def\s+\w+\s*\(",
        r"import\s+\w+",
        r"from\s+\w+\s+import",
        r"class\s+\w+.*:",
    ],
    SupportedLanguage.JAVA: [
        r"public\s+(class|interface|enum)",
        r"@\w+",
        r"package\s+\w+",
        r"import\s+[\w.]+;",
    ],
    SupportedLanguage.TYPESCRIPT: [
        r"interface\s+\w+",
        r":\s*\w+",
        r"export\s+(const|function|class|interface)",
        r"type\s+\w+\s*=",
    ],
    SupportedLanguage.JAVASCRIPT: [
        r"function\s+\w+\s*\(",
        r"const\s+\w+\s*=\s*\(.*\)\s*=>",
        r"export\s+(const|function|class)",
        r"require\s*\(",
    ],
}

# 语言特定的代码块标记
LANGUAGE_CODE_BLOCKS: Dict[str, str] = {
    SupportedLanguage.PYTHON: "python",
    SupportedLanguage.JAVA: "java",
    SupportedLanguage.TYPESCRIPT: "typescript",
    SupportedLanguage.JAVASCRIPT: "javascript",
}

# 语言特定的编码规范
LANGUAGE_STYLE_GUIDES: Dict[str, str] = {
    SupportedLanguage.PYTHON: "PEP 8",
    SupportedLanguage.JAVA: "Google Java Style Guide 或 Oracle Java Code Conventions",
    SupportedLanguage.TYPESCRIPT: "TypeScript Style Guide 和 ESLint 规则",
    SupportedLanguage.JAVASCRIPT: "JavaScript Style Guide (Airbnb 或 Google)",
}


def detect_language(code: str) -> Optional[str]:
    """
    检测代码的语言类型。

    Args:
        code: 代码字符串

    Returns:
        检测到的语言，如果无法检测则返回None
    """
    scores: Dict[str, int] = {lang: 0 for lang in SupportedLanguage}

    for lang, patterns in LANGUAGE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                scores[lang] += 1

    max_score = max(scores.values()) if scores else 0
    if max_score == 0:
        return None

    detected_lang = max(scores, key=scores.get)
    return detected_lang


def get_initial_prompt_template(language: str) -> str:
    """
    根据语言获取初始代码生成提示词模板。

    Args:
        language: 编程语言

    Returns:
        提示词模板字符串
    """
    style_guide = LANGUAGE_STYLE_GUIDES.get(language, "标准编码规范")
    lang_name = language.capitalize()

    return f"""
你是一位资深的{lang_name}程序员。请根据以下要求，编写{lang_name}代码。
你的代码必须包含完整的函数签名、文档字符串/注释，并遵循{style_guide}编码规范。

要求: {{task}}

请直接输出代码，不要包含任何额外的解释。
"""


def get_reflection_prompt_template(dimension: str, language: str) -> str:
    """
    根据维度和语言获取反思提示词模板。

    Args:
        dimension: 反思维度
        language: 编程语言

    Returns:
        提示词模板字符串
    """
    lang_name = language.capitalize()
    code_block = LANGUAGE_CODE_BLOCKS.get(language, language)

    templates: Dict[str, str] = {
        ReflectionDimension.PERFORMANCE: f"""
你是一位极其严格的代码评审专家和资深算法工程师，对代码的性能有极致的要求。
你的任务是审查以下{lang_name}代码，并专注于找出其在<strong>算法效率</strong>上的主要瓶颈。

# 原始任务:
{{task}}

# 待审查的代码:
```{code_block}
{{code}}
```

请分析该代码的时间复杂度和空间复杂度，并思考是否存在一种<strong>算法上更优</strong>的解决方案来显著提升性能。
如果存在，请清晰地指出当前算法的不足，并提出具体的、可行的改进算法建议（例如，使用哈希表替代线性查找，使用动态规划替代递归等）。
如果代码在算法层面已经达到最优，才能回答"无需改进"。

请直接输出你的反馈，不要包含任何额外的解释。
""",
        ReflectionDimension.FORMAT: f"""
你是一位严格的代码格式审查专家，专注于代码的可读性和一致性。
你的任务是审查以下{lang_name}代码，检查其是否符合{LANGUAGE_STYLE_GUIDES.get(language, "标准")}编码规范。

# 原始任务:
{{task}}

# 待审查的代码:
```{code_block}
{{code}}
```

请检查以下方面：
1. 缩进和空格使用是否一致
2. 命名规范（变量名、函数名、类名）是否符合规范
3. 代码行长度是否合理
4. 注释和文档字符串的格式是否正确
5. 导入语句的组织是否符合规范
6. 括号和换行的使用是否一致

如果代码格式完全符合规范，回答"无需改进"。否则，请明确指出需要改进的地方。

请直接输出你的反馈，不要包含任何额外的解释。
""",
        ReflectionDimension.SECURITY: f"""
你是一位资深的代码安全专家，专注于识别代码中的安全漏洞和风险。
你的任务是审查以下{lang_name}代码，找出潜在的安全问题。

# 原始任务:
{{task}}

# 待审查的代码:
```{code_block}
{{code}}
```

请检查以下安全方面：
1. 输入验证和清理（SQL注入、XSS、命令注入等）
2. 敏感信息处理（密码、密钥、令牌等）
3. 权限控制和访问控制
4. 资源管理和内存泄漏
5. 加密和哈希的使用是否正确
6. 错误处理是否泄露敏感信息
7. 依赖库的安全性问题

如果代码没有发现安全问题，回答"无需改进"。否则，请明确指出安全风险和建议的修复方案。

请直接输出你的反馈，不要包含任何额外的解释。
""",
        ReflectionDimension.BEST_PRACTICES: f"""
你是一位资深的{lang_name}开发专家，专注于代码的最佳实践和设计模式。
你的任务是审查以下{lang_name}代码，检查其是否符合最佳实践。

# 原始任务:
{{task}}

# 待审查的代码:
```{code_block}
{{code}}
```

请检查以下方面：
1. 代码结构和模块化设计
2. 设计模式的使用是否恰当
3. SOLID原则的遵循情况
4. DRY（Don't Repeat Yourself）原则
5. 错误处理和异常管理
6. 日志记录和调试支持
7. 代码的可测试性
8. 文档和注释的完整性

如果代码完全符合最佳实践，回答"无需改进"。否则，请明确指出需要改进的地方和具体的建议。

请直接输出你的反馈，不要包含任何额外的解释。
""",
        ReflectionDimension.LOGIC_ERRORS: f"""
你是一位资深的代码审查专家，专注于识别代码中的逻辑错误和潜在bug。
你的任务是审查以下{lang_name}代码，找出逻辑错误和可能导致运行时错误的问题。

# 原始任务:
{{task}}

# 待审查的代码:
```{code_block}
{{code}}
```

请检查以下方面：
1. 边界条件处理（空值、空数组、边界值等）
2. 循环和条件语句的逻辑是否正确
3. 变量初始化和作用域问题
4. 类型转换和类型检查
5. 算法逻辑的正确性
6. 资源释放和清理
7. 并发和线程安全问题（如果适用）

如果代码没有发现逻辑错误，回答"无需改进"。否则，请明确指出错误的位置和原因，以及修复建议。

请直接输出你的反馈，不要包含任何额外的解释。
""",
        ReflectionDimension.SYNTAX_ERRORS: f"""
你是一位资深的{lang_name}语法专家，专注于识别代码中的语法错误和编译错误。
你的任务是审查以下{lang_name}代码，找出语法错误。

# 原始任务:
{{task}}

# 待审查的代码:
```{code_block}
{{code}}
```

请检查以下方面：
1. 括号、大括号、方括号的匹配
2. 分号和逗号的使用是否正确
3. 关键字和保留字的使用
4. 类型声明和类型注解的语法
5. 导入语句的语法
6. 字符串和字符字面量的格式
7. 注释的语法

如果代码没有语法错误，回答"无需改进"。否则，请明确指出语法错误的位置和正确的写法。

请直接输出你的反馈，不要包含任何额外的解释。
""",
    }

    return templates.get(dimension, templates[ReflectionDimension.PERFORMANCE])


def get_refine_prompt_template(language: str) -> str:
    """
    根据语言获取代码优化提示词模板。

    Args:
        language: 编程语言

    Returns:
        提示词模板字符串
    """
    style_guide = LANGUAGE_STYLE_GUIDES.get(language, "标准编码规范")
    lang_name = language.capitalize()

    return f"""
你是一位资深的{lang_name}程序员。你正在根据代码评审专家的多维度反馈来优化你的代码。

# 原始任务:
{{task}}

# 你上一轮尝试的代码:
{{last_code_attempt}}

# 多维度评审反馈:
{{feedback}}

请根据评审专家的反馈，生成一个优化后的新版本代码。
你的代码必须包含完整的函数签名、文档字符串/注释，并遵循{style_guide}编码规范。
请直接输出优化后的代码，不要包含任何额外的解释。
"""

class Memory:
    """记忆类，用于存储代码执行和反思的历史记录。"""

    def __init__(self) -> None:
        """初始化记忆存储。"""
        self.records: List[Dict[str, Any]] = []

    def add_record(self, record_type: str, content: str, dimension: Optional[str] = None) -> None:
        """
        添加一条记忆记录。

        Args:
            record_type: 记录类型（execution, reflection等）
            content: 记录内容
            dimension: 反思维度（仅用于reflection类型）
        """
        record: Dict[str, Any] = {"type": record_type, "content": content}
        if dimension:
            record["dimension"] = dimension
        self.records.append(record)
        if dimension:
            print(f"memory update, add a {record_type} ({dimension}) content")
        else:
            print(f"memory update, add a {record_type} content")

    def get_trajectory(self) -> str:
        """
        获取完整的执行轨迹。

        Returns:
            格式化的轨迹字符串
        """
        trajectory_parts: List[str] = []
        for record in self.records:
            if record["type"] == "execution":
                trajectory_parts.append(f"---prior round of trials---\n{record['content']}")
            elif record["type"] == "reflection":
                dimension = record.get("dimension", "unknown")
                trajectory_parts.append(
                    f"---review feedback ({dimension})---\n{record['content']}"
                )

        return "\n\n".join(trajectory_parts)

    def get_last_execution(self) -> Optional[str]:
        """
        获取最后一次执行的代码。

        Returns:
            最后一次执行的代码字符串，如果不存在则返回None
        """
        for record in reversed(self.records):
            if record["type"] == "execution":
                return record["content"]
        return None

    def get_all_reflections(self) -> Dict[str, str]:
        """
        获取所有维度的反思反馈。

        Returns:
            字典，键为维度名称，值为反馈内容
        """
        reflections: Dict[str, str] = {}
        for record in reversed(self.records):
            if record["type"] == "reflection" and "dimension" in record:
                dimension = record["dimension"]
                if dimension not in reflections:
                    reflections[dimension] = record["content"]
        return reflections

class ReflectionAgent:
    """
    多维度反思代理，支持从多个角度审查和改进代码。

    支持的维度：
    - 性能 (Performance)
    - 格式 (Format)
    - 安全 (Security)
    - 最佳实践 (Best Practices)
    - 逻辑错误 (Logic Errors)
    - 语法错误 (Syntax Errors)

    支持的语言：
    - Python
    - Java
    - TypeScript
    - JavaScript
    """

    def __init__(
        self,
        llm_client: GeneralLLMClient,
        max_iterations: int = 3,
        dimensions: Optional[List[str]] = None,
        language: Optional[str] = None,
    ) -> None:
        """
        初始化反思代理。

        Args:
            llm_client: LLM客户端实例
            max_iterations: 最大迭代次数
            dimensions: 要使用的反思维度列表，如果为None则使用所有维度
            language: 编程语言，如果为None则自动检测
        """
        self.llm_client = llm_client
        self.memory = Memory()
        self.max_iterations = max_iterations
        self.dimensions = dimensions or [
            ReflectionDimension.PERFORMANCE,
            ReflectionDimension.FORMAT,
            ReflectionDimension.SECURITY,
            ReflectionDimension.BEST_PRACTICES,
            ReflectionDimension.LOGIC_ERRORS,
            ReflectionDimension.SYNTAX_ERRORS,
        ]
        self.language = language

    def run(self, task: str, language: Optional[str] = None) -> Optional[str]:
        """
        运行反思代理，生成并优化代码。

        Args:
            task: 任务描述
            language: 编程语言，如果提供则覆盖初始化时的设置

        Returns:
            最终优化后的代码，如果失败则返回None
        """
        # 确定使用的语言
        detected_language = language or self.language

        # 生成初始代码
        print("\n-> Generating initial code...")
        initial_code = self._generate_initial_code(task, detected_language)
        if not initial_code:
            print("Error: Failed to generate initial code")
            return None

        # 如果语言未指定，从初始代码中检测
        if not detected_language:
            detected_language = detect_language(initial_code)
            if not detected_language:
                detected_language = SupportedLanguage.PYTHON  # 默认使用Python
            print(f"Detected language: {detected_language}")

        self.language = detected_language
        self.memory.add_record("execution", initial_code)

        # 迭代优化
        for iteration in range(self.max_iterations):
            print(f"\n-> Iteration {iteration + 1}/{self.max_iterations}")

            last_code = self.memory.get_last_execution()
            if not last_code:
                break

            # 多维度反思
            print("\n-> Reflecting on multiple dimensions...")
            all_feedback = self._reflect_all_dimensions(task, last_code, detected_language)

            # 检查是否所有维度都无需改进
            if self._all_dimensions_no_improvement(all_feedback):
                print("All dimensions indicate no improvement needed. Task finished.")
                break

            # 汇总反馈并优化代码
            print("\n-> Optimizing code based on feedback...")
            combined_feedback = self._combine_feedback(all_feedback)
            refined_code = self._refine_code(task, last_code, combined_feedback, detected_language)

            if not refined_code:
                print("Error: Failed to refine code")
                break

            self.memory.add_record("execution", refined_code)

        final_code = self.memory.get_last_execution()
        if final_code:
            code_block = LANGUAGE_CODE_BLOCKS.get(detected_language, "code")
            print(f"\n-- Task finished ---\nFinal code:\n```{code_block}\n{final_code}\n```")
        return final_code

    def _generate_initial_code(self, task: str, language: Optional[str] = None) -> Optional[str]:
        """
        生成初始代码。

        Args:
            task: 任务描述
            language: 编程语言

        Returns:
            生成的代码字符串
        """
        if not language:
            language = SupportedLanguage.PYTHON

        template = get_initial_prompt_template(language)
        prompt = template.format(task=task)
        return self._get_llm_response(prompt)

    def _reflect_all_dimensions(
        self, task: str, code: str, language: str
    ) -> Dict[str, str]:
        """
        对所有维度进行反思。

        Args:
            task: 任务描述
            code: 待审查的代码
            language: 编程语言

        Returns:
            字典，键为维度名称，值为反馈内容
        """
        feedbacks: Dict[str, str] = {}

        for dimension in self.dimensions:
            print(f"  - Reflecting on {dimension}...")
            template = get_reflection_prompt_template(dimension, language)
            prompt = template.format(task=task, code=code)
            feedback = self._get_llm_response(prompt)

            if feedback:
                feedbacks[dimension] = feedback
                self.memory.add_record("reflection", feedback, dimension=dimension)

        return feedbacks

    def _combine_feedback(self, feedbacks: Dict[str, str]) -> str:
        """
        合并所有维度的反馈。

        Args:
            feedbacks: 各维度的反馈字典

        Returns:
            合并后的反馈字符串
        """
        if not feedbacks:
            return "No feedback available."

        combined_parts: List[str] = []
        for dimension, feedback in feedbacks.items():
            dimension_name = dimension.replace("_", " ").title()
            combined_parts.append(f"## {dimension_name} Review:\n{feedback}")

        return "\n\n".join(combined_parts)

    def _all_dimensions_no_improvement(self, feedbacks: Dict[str, str]) -> bool:
        """
        检查是否所有维度都表示无需改进。

        Args:
            feedbacks: 各维度的反馈字典

        Returns:
            如果所有维度都无需改进则返回True
        """
        if not feedbacks:
            return False

        no_improvement_keywords = ["无需改进", "无需修改", "无需优化", "no improvement", "no changes needed"]
        for feedback in feedbacks.values():
            feedback_lower = feedback.lower()
            if not any(keyword.lower() in feedback_lower for keyword in no_improvement_keywords):
                return False
        return True

    def _refine_code(
        self, task: str, last_code: str, feedback: str, language: str
    ) -> Optional[str]:
        """
        根据反馈优化代码。

        Args:
            task: 任务描述
            last_code: 上一轮尝试的代码
            feedback: 评审反馈
            language: 编程语言

        Returns:
            优化后的代码字符串
        """
        template = get_refine_prompt_template(language)
        prompt = template.format(
            task=task, last_code_attempt=last_code, feedback=feedback
        )
        return self._get_llm_response(prompt)

    def _get_llm_response(self, prompt: str) -> Optional[str]:
        """
        获取LLM响应。

        Args:
            prompt: 提示词

        Returns:
            LLM响应文本，如果失败则返回None
        """
        messages = [{"role": "user", "content": prompt}]
        response_text = self.llm_client.think(messages=messages)
        return response_text if response_text else None


if __name__ == "__main__":
    llm = GeneralLLMClient()
    # 使用所有维度进行反思
    agent = ReflectionAgent(llm_client=llm, max_iterations=3)
    question = "编写一个Python函数，实现冒泡排序"
    result = agent.run(question)
    if result:
        print("\n✅ Code generation and optimization completed successfully!")
    else:
        print("\n❌ Code generation failed.")
