import os
import sys

if __package__ is None:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import re
from typing import Any, Dict, Literal, Optional, Tuple, Union

from pydantic import BaseModel, Field, ValidationError

from core import GeneralLLMClient
from tools.get_weather import get_weather
from tools.tool_executor import ToolExecutor


# Pydantic 模型定义
class ToolAction(BaseModel):
    """工具调用动作模型。"""

    type: Literal["tool"] = "tool"
    name: str = Field(..., description="工具名称")
    input: str = Field(..., description="工具输入参数")


class FinishAction(BaseModel):
    """完成动作模型。"""

    type: Literal["finish"] = "finish"
    answer: str = Field(..., description="最终答案")


class ReActResponse(BaseModel):
    """ReAct 响应模型。"""

    thought: str = Field(default="", description="思考过程")
    action: Union[ToolAction, FinishAction] = Field(..., description="动作")


# ReAct 提示词模板
REACT_PROMPT_TEMPLATE = """
请注意，你是一个有能力调用外部工具的智能助手。

可用工具如下:
{tools}

请严格按照以下JSON格式进行回应，只输出JSON，不要包含其他文字:

{{
  "thought": "你的思考过程，用于分析问题、拆解任务和规划下一步行动",
  "action": {{
    "type": "tool" 或 "finish",
    "name": "工具名称（当type为tool时必填）",
    "input": "工具输入参数（当type为tool时必填）",
    "answer": "最终答案（当type为finish时必填）"
  }}
}}

示例1 - 调用工具:
{{
  "thought": "用户想知道广州的天气，我需要调用天气查询工具",
  "action": {{
    "type": "tool",
    "name": "get_weather",
    "input": "广州"
  }}
}}

示例2 - 完成并返回答案:
{{
  "thought": "我已经获得了天气信息，可以回答用户的问题了",
  "action": {{
    "type": "finish",
    "answer": "今天广州天气晴朗，温度25度，适合旅游"
  }}
}}

现在，请开始解决以下问题:
Question: {question}
History: {history}
"""

class ReActAgent:
    def __init__(self, llm_client: GeneralLLMClient, tool_executor: ToolExecutor, max_steps: int = 5):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history = []

    def run(self, question: str) -> Optional[str]:
        """
        Run the ReAct agent.

        Args:
            question: 用户的问题

        Returns:
            最终答案字符串，如果达到最大步数仍未完成则返回None
        """
        self.history = []
        current_step = 0
        while current_step < self.max_steps:
            current_step += 1
            print(f"Step {current_step}:")

            tools_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history)
            prompt = REACT_PROMPT_TEMPLATE.format(question=question, tools=tools_desc, history=history_str)

            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages)

            if not response_text:
                print("Error: No response from LLM")
                break

            thought, action = self._parse_output(response_text)
            if thought:
                print(f"Thought: {thought}")
            if not action:
                print("Error: No action found in response")
                break

            action_type = action.get("type")
            if action_type == "finish":
                finish_answer = action.get("answer", "")
                print(f"Final Answer: {finish_answer}")
                return finish_answer

            if action_type != "tool":
                print(f"Error: Unknown action type: {action_type}")
                break

            tool_name = action.get("name")
            tool_input = action.get("input")
            if not tool_name or not tool_input:
                print("Error: Missing tool name or input")
                continue
            print(f"Action: {tool_name} [{tool_input}]")

            tool_function = self.tool_executor.getTool(tool_name)
            if not tool_function:
                observation = f"Error: Tool {tool_name} not found"
            else:
                observation = tool_function(tool_input)

            print(f"Observation: {observation}")

            # 将 action 格式化为字符串以便记录历史
            if action_type == "tool":
                action_str = f"{tool_name}[{tool_input}]"
            else:
                action_str = f"Finish[{action.get('answer', '')}]"
            self.history.append(f"Action: {action_str}")
            self.history.append(f"Observation: {observation}")

        return None

    def _parse_output(self, text: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        解析LLM的JSON格式输出，优先使用Pydantic验证，失败时使用正则表达式作为后备。

        Args:
            text: LLM返回的文本，应该包含JSON格式的响应

        Returns:
            元组，包含 (thought, action)
            - thought: 思考内容字符串，如果解析失败则为None
            - action: 包含action信息的字典，如果解析失败则为None
        """
        # 首先尝试使用Pydantic验证JSON
        parsed_response = self._parse_with_pydantic(text)
        if parsed_response:
            return parsed_response

        # 如果Pydantic验证失败，使用正则表达式作为后备
        print("⚠️ JSON解析失败，尝试使用正则表达式解析...")
        return self._parse_with_regex(text)

    def _parse_with_pydantic(self, text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        使用Pydantic验证和解析JSON输出。

        Args:
            text: LLM返回的文本

        Returns:
            如果解析成功，返回 (thought, action_dict)，否则返回None
        """
        try:
            # 提取JSON部分
            json_text = self._extract_json(text)
            if not json_text:
                return None

            # 解析JSON
            parsed = json.loads(json_text)

            # 使用Pydantic验证
            response = ReActResponse.model_validate(parsed)

            # 转换为字典格式
            action_dict = response.action.model_dump()

            return response.thought, action_dict
        except (json.JSONDecodeError, ValidationError):
            return None
        except Exception:
            return None

    def _parse_with_regex(self, text: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        使用正则表达式解析输出，处理边缘情况。

        Args:
            text: LLM返回的文本

        Returns:
            元组，包含 (thought, action)
        """
        try:
            # 提取thought
            thought_patterns = [
                r"Thought:\s*(.+?)(?=\nAction:|\n*$)",  # 标准格式
                r"思考[：:]\s*(.+?)(?=\n行动|\nAction:|\n*$)",  # 中文格式
                r'"thought"\s*:\s*"([^"]+)"',  # JSON格式中的thought
                r"'thought'\s*:\s*'([^']+)'",  # 单引号JSON格式
            ]

            thought = None
            for pattern in thought_patterns:
                match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if match:
                    thought = match.group(1).strip()
                    break

            # 提取action
            action = None

            # 尝试解析Finish动作
            finish_patterns = [
                r'Finish\[([^\]]+)\]',  # Finish[answer]
                r'"type"\s*:\s*"finish"[^}]*"answer"\s*:\s*"([^"]+)"',  # JSON格式
                r"'type'\s*:\s*'finish'[^}]*'answer'\s*:\s*'([^']+)'",  # 单引号JSON格式
                r"Action:\s*Finish\[([^\]]+)\]",  # Action: Finish[answer]
                r"完成[：:]\s*(.+?)(?=\n|$)",  # 中文格式
            ]

            for pattern in finish_patterns:
                match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if match:
                    answer = match.group(1).strip()
                    action = {"type": "finish", "answer": answer}
                    break

            # 如果还没找到，尝试解析工具调用
            if not action:
                tool_patterns = [
                    r'(\w+)\[([^\]]+)\]',  # tool_name[input]
                    r'"type"\s*:\s*"tool"[^}]*"name"\s*:\s*"([^"]+)"[^}]*"input"\s*:\s*"([^"]+)"',  # JSON格式
                    r"'type'\s*:\s*'tool'[^}]*'name'\s*:\s*'([^']+)'[^}]*'input'\s*:\s*'([^']+)'",  # 单引号JSON格式
                    r"Action:\s*(\w+)\[([^\]]+)\]",  # Action: tool_name[input]
                ]

                for pattern in tool_patterns:
                    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                    if match:
                        tool_name = match.group(1).strip()
                        tool_input = match.group(2).strip()
                        # 跳过Finish，因为已经处理过了
                        if tool_name.lower() != "finish":
                            action = {"type": "tool", "name": tool_name, "input": tool_input}
                            break

            if not action:
                return thought, None

            return thought, action
        except Exception as e:
            print(f"Error parsing with regex: {e}")
            return None, None

    def _extract_json(self, text: str) -> Optional[str]:
        """
        从文本中提取JSON部分。

        Args:
            text: 可能包含JSON的文本

        Returns:
            提取的JSON字符串，如果未找到则返回None
        """
        text = text.strip()

        # 如果文本被```json```包裹，提取JSON部分
        if text.startswith("```"):
            lines = text.split("\n")
            json_lines = []
            in_json_block = False
            for line in lines:
                if line.strip().startswith("```json") or (line.strip().startswith("```") and not in_json_block):
                    in_json_block = True
                    continue
                if line.strip() == "```" and in_json_block:
                    break
                if in_json_block:
                    json_lines.append(line)
            if json_lines:
                return "\n".join(json_lines)

        # 尝试找到JSON对象（从第一个{到最后一个}）
        brace_start = text.find("{")
        if brace_start != -1:
            # 从第一个{开始，找到匹配的最后一个}
            brace_count = 0
            for i in range(brace_start, len(text)):
                if text[i] == "{":
                    brace_count += 1
                elif text[i] == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        return text[brace_start : i + 1]

        # 如果都没找到，返回原文本（可能是纯JSON）
        return text if text.startswith("{") else None


if __name__ == '__main__':
    llm = GeneralLLMClient()
    tool_executor = ToolExecutor()
    tool_description = "一个天气查询工具。当你需要回答某个地区的天气时，应使用此工具。"
    tool_executor.registerTool("get_weather", tool_description, get_weather)
    agent = ReActAgent(llm_client=llm, tool_executor=tool_executor)
    question = "华为手机哪一款性价比最高"
    result = agent.run(question)
    print(f"Result: {result}")
