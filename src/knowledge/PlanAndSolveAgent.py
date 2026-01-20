import json
import os
import sys
from typing import Optional

if __package__ is None:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from core import GeneralLLMClient

PLANNER_PROMPT_TEMPLATE = """
你是一个顶级的AI规划专家。你的任务是将用户提出的复杂问题分解成一个由多个简单步骤组成的行动计划。
请确保计划中的每个步骤都是一个独立的、可执行的子任务，并且严格按照逻辑顺序排列。
你的输出必须是一个JSON数组，其中每个元素都是一个描述子任务的对象，包含以下字段：
- id: 步骤的序号（从1开始的整数）
- title: 步骤的简要标题
- detail: 步骤的详细说明，包含需要执行的具体内容
- type: 步骤类型（如analysis / planning / execution / summary等）
- depends_on: 该步骤依赖的前置步骤id列表

问题: {question}

请严格按照以下格式输出你的计划，```json 与 ``` 作为前后缀是必要的，且不得输出任何多余解释文字:
```json
[
  {{
    "id": 1,
    "title": "步骤标题1",
    "detail": "步骤1的详细说明，包含需要执行的具体内容。",
    "type": "analysis",
    "depends_on": []
  }},
  {{
    "id": 2,
    "title": "步骤标题2",
    "detail": "步骤2的详细说明。",
    "type": "planning",
    "depends_on": [1]
  }}
]
```
"""

REPLANNER_PROMPT_TEMPLATE = """
你是一个顶级的AI规划专家。当前计划在执行过程中遇到了问题，需要你根据执行历史重新规划剩余步骤。

# 原始问题:
{question}

# 原始计划:
{original_plan}

# 执行历史（已完成的步骤和结果）:
{execution_history}

# 当前失败的步骤:
{failed_step}

# 失败原因或问题描述:
{failure_reason}

请根据以上信息，重新规划剩余步骤。你需要：
1. 考虑已经成功完成的步骤和结果（这些步骤已经完成，不需要重新执行）
2. 修改或替换失败的步骤
3. 调整后续步骤以适应新的情况

请严格按照以下格式输出你的新计划，```json 与 ``` 作为前后缀是必要的，且不得输出任何多余解释文字:
```json
[
  {{
    "id": 1,
    "title": "步骤标题1",
    "detail": "步骤1的详细说明，包含需要执行的具体内容。",
    "type": "analysis",
    "depends_on": []
  }},
  {{
    "id": 2,
    "title": "步骤标题2",
    "detail": "步骤2的详细说明。",
    "type": "planning",
    "depends_on": [1]
  }}
]
```

注意：新计划应该只包含从失败步骤开始的剩余需要完成的步骤。可以修改失败的步骤或添加新的步骤来替代它。
"""

EXECUTOR_PROMPT_TEMPLATE = """
你是一位顶级的AI执行专家。你的任务是严格按照给定的计划，一步步地解决问题。
你将收到原始问题、完整的计划、以及到目前为止已经完成的步骤和结果。
请你专注于解决"当前步骤"，并仅输出该步骤的最终答案，不要输出任何额外的解释或对话。

# 原始问题:
{question}

# 完整计划:
{plan}

# 历史步骤与结果:
{history}

# 当前步骤:
{current_step}

请仅输出针对"当前步骤"的回答:
"""

STEP_VALIDATION_PROMPT_TEMPLATE = """
你是一位严格的步骤验证专家。你的任务是判断当前步骤的执行结果是否成功。

# 原始问题:
{question}

# 当前步骤:
{current_step}

# 步骤执行结果:
{step_result}

请判断该步骤是否成功完成。如果成功，回答"成功"；如果失败或不符合预期，回答"失败"并简要说明原因。

请严格按照以下格式输出:
成功/失败: [你的判断]
原因: [如果失败，说明原因；如果成功，可以省略]
"""


class Planner:
    """规划器类，负责生成初始计划和动态重规划。"""

    def __init__(self, llm_client: GeneralLLMClient) -> None:
        """
        初始化规划器。

        Args:
            llm_client: LLM客户端实例
        """
        self.llm_client = llm_client

    def plan(self, question: str) -> list[str]:
        """
        生成初始计划。

        Args:
            question: 用户问题

        Returns:
            计划步骤列表（每个元素为格式化后的步骤描述字符串）
        """
        prompt = PLANNER_PROMPT_TEMPLATE.format(question=question)

        messages = [{"role": "user", "content": prompt}]

        print("-- planning --")

        response_text = self.llm_client.think(messages=messages) or ""

        print(f"Planner response: {response_text}")

        try:
            if "```json" in response_text:
                plan_str = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
            else:
                plan_str = response_text.strip()

            steps_data = json.loads(plan_str)
            if not isinstance(steps_data, list):
                return []

            formatted_steps: list[str] = []
            for step in steps_data:
                if isinstance(step, dict):
                    title = str(step.get("title", "")).strip()
                    detail = str(step.get("detail", "")).strip()
                    if title and detail:
                        formatted_steps.append(f"{title}: {detail}")
                    elif title:
                        formatted_steps.append(title)
                    else:
                        formatted_steps.append(json.dumps(step, ensure_ascii=False))
                else:
                    formatted_steps.append(str(step))

            return formatted_steps
        except (ValueError, json.JSONDecodeError, IndexError) as e:
            print(f"parse plan error: {e}")
            print(f"original response: {response_text}")
            return []
        except Exception as e:
            print(f"unexpected error: {e}")
            return []

    def replan(
        self,
        question: str,
        original_plan: list[str],
        execution_history: str,
        failed_step: str,
        failure_reason: str,
    ) -> list[str]:
        """
        基于执行历史重新规划剩余步骤。

        Args:
            question: 原始问题
            original_plan: 原始计划
            execution_history: 执行历史（已完成的步骤和结果）
            failed_step: 失败的步骤
            failure_reason: 失败原因

        Returns:
            新的计划步骤列表
        """
        prompt = REPLANNER_PROMPT_TEMPLATE.format(
            question=question,
            original_plan=original_plan,
            execution_history=execution_history,
            failed_step=failed_step,
            failure_reason=failure_reason,
        )

        messages = [{"role": "user", "content": prompt}]

        print("-- replanning --")

        response_text = self.llm_client.think(messages=messages) or ""

        print(f"Replanner response: {response_text}")

        try:
            if "```json" in response_text:
                plan_str = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
            else:
                plan_str = response_text.strip()

            steps_data = json.loads(plan_str)
            if not isinstance(steps_data, list):
                return []

            formatted_steps: list[str] = []
            for step in steps_data:
                if isinstance(step, dict):
                    title = str(step.get("title", "")).strip()
                    detail = str(step.get("detail", "")).strip()
                    if title and detail:
                        formatted_steps.append(f"{title}: {detail}")
                    elif title:
                        formatted_steps.append(title)
                    else:
                        formatted_steps.append(json.dumps(step, ensure_ascii=False))
                else:
                    formatted_steps.append(str(step))

            return formatted_steps
        except (ValueError, json.JSONDecodeError, IndexError) as e:
            print(f"parse replan error: {e}")
            print(f"original response: {response_text}")
            return []
        except Exception as e:
            print(f"unexpected error: {e}")
            return []

class Executor:
    """执行器类，负责执行计划步骤并验证步骤结果。"""

    def __init__(self, llm_client: GeneralLLMClient) -> None:
        """
        初始化执行器。

        Args:
            llm_client: LLM客户端实例
        """
        self.llm_client = llm_client

    def validate_step(
        self, question: str, current_step: str, step_result: str
    ) -> tuple[bool, Optional[str]]:
        """
        验证步骤执行结果是否成功。

        Args:
            question: 原始问题
            current_step: 当前步骤
            step_result: 步骤执行结果

        Returns:
            元组 (是否成功, 失败原因)，如果成功则失败原因为None
        """
        prompt = STEP_VALIDATION_PROMPT_TEMPLATE.format(
            question=question, current_step=current_step, step_result=step_result
        )

        messages = [{"role": "user", "content": prompt}]

        response_text = self.llm_client.think(messages=messages) or ""

        # 解析验证结果
        if "成功" in response_text or "success" in response_text.lower():
            return True, None

        # 提取失败原因
        failure_reason = None
        if "原因:" in response_text:
            failure_reason = response_text.split("原因:")[-1].strip()
        elif "reason:" in response_text.lower():
            failure_reason = response_text.split("reason:")[-1].strip()
        else:
            failure_reason = response_text.strip()

        return False, failure_reason

    def execute_step(
        self, question: str, plan: list[str], history: str, current_step: str
    ) -> str:
        """
        执行单个步骤。

        Args:
            question: 原始问题
            plan: 完整计划
            history: 执行历史
            current_step: 当前步骤

        Returns:
            步骤执行结果
        """
        prompt = EXECUTOR_PROMPT_TEMPLATE.format(
            question=question, plan=plan, history=history, current_step=current_step
        )

        messages = [{"role": "user", "content": prompt}]

        response_text = self.llm_client.think(messages=messages) or ""
        return response_text

    def execute(
        self, question: str, plan: list[str], start_index: int = 0
    ) -> tuple[str, str, Optional[tuple[int, str, str]]]:
        """
        执行计划步骤。

        Args:
            question: 原始问题
            plan: 计划步骤列表
            start_index: 开始执行的步骤索引

        Returns:
            元组 (最终答案, 执行历史, 失败信息)
            失败信息为元组 (失败步骤索引, 失败步骤, 失败原因)，如果全部成功则为None
        """
        history = ""

        print("\n-- executing --")

        for i in range(start_index, len(plan)):
            step = plan[i]

            response_text = self.execute_step(question, plan, history, step)

            # 验证步骤结果
            is_success, failure_reason = self.validate_step(question, step, response_text)

            if not is_success:
                print(f"step {i+1} failed: {step}")
                print(f"failure reason: {failure_reason}")
                return (
                    response_text,
                    history,
                    (i, step, failure_reason or "步骤执行失败"),
                )

            history += f"Step {i+1}: {step}\nResult: {response_text}\n\n"

            print(f"step {i+1} success, result: {response_text}")

        final_answer = response_text
        return final_answer, history, None

class PlanAndSolveAgent:
    """
    规划与求解代理，支持动态重规划机制。

    当执行过程中发现某个步骤无法完成或结果不符合预期时，会自动触发重规划。
    """

    def __init__(
        self, llm_client: GeneralLLMClient, max_replan_attempts: int = 3
    ) -> None:
        """
        初始化代理。

        Args:
            llm_client: LLM客户端实例
            max_replan_attempts: 最大重规划次数，默认为3次
        """
        self.llm_client = llm_client
        self.planner = Planner(llm_client)
        self.executor = Executor(llm_client)
        self.max_replan_attempts = max_replan_attempts

    def run(self, question: str) -> Optional[str]:
        """
        运行代理，执行规划、执行和动态重规划流程。

        Args:
            question: 用户问题

        Returns:
            最终答案，如果失败则返回None
        """
        print(f"\n-- running {question} --")

        # 生成初始计划
        plan = self.planner.plan(question)

        if not plan:
            print("\n-- no plan found --")
            return None

        execution_history = ""
        replan_count = 0
        current_step_index = 0

        while True:
            # 执行计划
            final_answer, history, failure_info = self.executor.execute(
                question, plan, start_index=current_step_index
            )

            # 更新执行历史
            if history:
                execution_history = history

            # 如果执行成功，返回最终答案
            if failure_info is None:
                print(f"\n-- solve success, final answer: {final_answer} --")
                return final_answer

            # 如果达到最大重规划次数，停止
            if replan_count >= self.max_replan_attempts:
                print(
                    f"\n-- max replan attempts ({self.max_replan_attempts}) reached, stopping --"
                )
                print(f"Failed at step {failure_info[0] + 1}: {failure_info[1]}")
                print(f"Failure reason: {failure_info[2]}")
                return None

            # 触发重规划
            failed_step_index, failed_step, failure_reason = failure_info
            print(f"\n-- step {failed_step_index + 1} failed, triggering replan --")

            new_plan = self.planner.replan(
                question=question,
                original_plan=plan,
                execution_history=execution_history,
                failed_step=failed_step,
                failure_reason=failure_reason or "步骤执行失败",
            )

            if not new_plan:
                print("\n-- replan failed, no new plan generated --")
                return None

            # 更新计划：重规划返回的是剩余步骤，需要从失败步骤的位置开始执行
            plan = new_plan
            current_step_index = 0  # 重规划后的计划从第一步开始执行（因为新计划只包含剩余步骤）
            replan_count += 1

            print(f"-- replan attempt {replan_count}/{self.max_replan_attempts} --")
            print(f"New plan (remaining steps): {plan}")


if __name__ == '__main__':
    """
    主函数：演示动态重规划能力。

    这个示例展示了一个可能触发重规划的场景：
    - 任务包含可能无法完成的约束条件
    - 初始计划可能会失败
    - 重规划机制会自动调整计划
    """
    llm = GeneralLLMClient()
    # 设置最大重规划次数，以便观察重规划过程
    agent = PlanAndSolveAgent(llm_client=llm, max_replan_attempts=3)

    # 示例1: 明显约束冲突的任务（便于观察重规划是否发生）
    # 期望现象：初始计划难以同时满足所有条件，某些步骤可能被判定为“失败”，触发重规划
    print("=" * 80)
    print("示例1: 约束冲突场景（用于测试重规划触发）")
    print("=" * 80)
    question1 = (
        "规划一个3天的欧洲旅行，要求："
        "1. 预算不超过1000元人民币 2. 至少访问5个国家 3. 每个国家至少停留1天 "
        "4. 全程只使用公共交通 5. 住宿必须是四星级以上酒店"
    )
    print(f"问题: {question1}\n")
    result1 = agent.run(question1)
    print(f"\n最终结果: {result1}")

    # 示例2: 描述模糊、需求不清晰的任务（用于测试重规划对计划细化的能力）
    # 期望现象：初始计划可能过于粗糙或不可执行，经过重规划后步骤会更具体、更可执行
    print("\n" + "=" * 80)
    print("示例2: 模糊需求场景（用于测试计划细化和重规划）")
    print("=" * 80)
    question2 = (
        "帮我规划一个周末团建活动，要求："
        "1. 大家既要放松又要提升团队协作 2. 预算尽量低但体验要“高端” "
        "3. 活动地点离市区既不能太远也不能太近 4. 具体形式你来帮我想"
    )
    print(f"问题: {question2}\n")
    result2 = agent.run(question2)
    print(f"\n最终结果: {result2}")
