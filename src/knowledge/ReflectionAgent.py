import os
import sys
from typing import Dict, List, Optional

if __package__ is None:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from core import GeneralLLMClient

INITIAL_PROMPT_TEMPLATE = """
你是一位资深的Python程序员。请根据以下要求，编写一个Python函数。
你的代码必须包含完整的函数签名、文档字符串，并遵循PEP 8编码规范。

要求: {task}

请直接输出代码，不要包含任何额外的解释。
"""

REFLECT_PROMPT_TEMPLATE = """
你是一位极其严格的代码评审专家和资深算法工程师，对代码的性能有极致的要求。
你的任务是审查以下Python代码，并专注于找出其在<strong>算法效率</strong>上的主要瓶颈。

# 原始任务:
{task}

# 待审查的代码:
```python
{code}
```

请分析该代码的时间复杂度，并思考是否存在一种<strong>算法上更优</strong>的解决方案来显著提升性能。
如果存在，请清晰地指出当前算法的不足，并提出具体的、可行的改进算法建议（例如，使用筛法替代试除法）。
如果代码在算法层面已经达到最优，才能回答“无需改进”。

请直接输出你的反馈，不要包含任何额外的解释。
"""

REFINE_PROMPT_TEMPLATE = """
你是一位资深的Python程序员。你正在根据一位代码评审专家的反馈来优化你的代码。

# 原始任务:
{task}

# 你上一轮尝试的代码:
{last_code_attempt}
评审员的反馈：
{feedback}

请根据评审员的反馈，生成一个优化后的新版本代码。
你的代码必须包含完整的函数签名、文档字符串，并遵循PEP 8编码规范。
请直接输出优化后的代码，不要包含任何额外的解释。
"""

class Memory:
    def __init__(self):
        self.records:  List[Dict[str, any]] = []

    def add_record(self, record_type: str, content: str):
        """
        添加一条记忆记录
        Args:
        - record_type: 记录类型
        - content: 记录内容
        """
        record = {"type": record_type, "content": content}
        self.records.append(record)
        print(f"memory update, add a {record_type} content")

    def get_trajectory(self) -> str:
        trajectory_parts = []
        for record in self.records:
            if record["type"] == "execution":
                trajectory_parts.append(f"---prior round of trials---\n{record['content']}")
            elif record["type"] == "reflection":
                trajectory_parts.append(f"---review feedback---\n{record['content']}")

        return "\n\n".join(trajectory_parts)

    def get_last_execution(self) -> Optional[str]:
        for record in reversed(self.records):
            if record["type"] == "execution":
                return record["content"]
        return None

class ReflectionAgent:
    def __init__(self, llm_client: GeneralLLMClient, max_iterations: int = 3):
        self.llm_client = llm_client
        self.memory = Memory()
        self.max_iterations = max_iterations

    def run(self, task: str):
        initial_prompt = INITIAL_PROMPT_TEMPLATE.format(task=task)
        initial_code = self._get_llm_response(initial_prompt)
        self.memory.add_record("execution", initial_code)

        for _i in range(self.max_iterations):
            print(f"\n-> in the {_i+1}/{self.max_iterations} round of iteration")

            print("\n-> reflecting...")
            last_code = self.memory.get_last_execution()
            reflection_prompt = REFLECT_PROMPT_TEMPLATE.format(task=task, code=last_code)
            feedback = self._get_llm_response(reflection_prompt)
            self.memory.add_record("reflection", feedback)

            if "无需改进" in feedback:
                print("task finished")
                break

            print("\n-> under optimization")
            refine_prompt = REFINE_PROMPT_TEMPLATE.format(task=task, last_code_attempt=last_code, feedback=feedback)
            refined_code = self._get_llm_response(refine_prompt)
            self.memory.add_record("execution", refined_code)

        final_code = self.memory.get_last_execution()
        print(f"\n-- task finished ---\nfinal code:\n```python\n{final_code}\n```")
        return final_code

    def _get_llm_response(self, prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        response_text = self.llm_client.think(messages=messages) or ""
        return response_text


if __name__ == '__main__':
    llm = GeneralLLMClient()
    agent = ReflectionAgent(llm_client=llm)
    question = "编写一个Python函数，实现冒泡排序"
    agent.run(question)
