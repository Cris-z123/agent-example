import sys, os
if __package__ is None:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import re
from core import GeneralLLMClient
from tools.tool_executor import ToolExecutor
from tools.get_weather import get_weather


# ReAct 提示词模板
REACT_PROMPT_TEMPLATE = """
请注意，你是一个有能力调用外部工具的智能助手。

可用工具如下:
{tools}

请严格按照以下格式进行回应:

Thought: 你的思考过程，用于分析问题、拆解任务和规划下一步行动。
Action: 你决定采取的行动，必须是以下格式之一:
- `{{tool_name}}[{{tool_input}}]`:调用一个可用工具。
- `Finish[最终答案]`:当你认为已经获得最终答案时。
- 当你收集到足够的信息，能够回答用户的最终问题时，你必须在Action:字段后使用 finish(answer="...") 来输出最终答案。

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

    def run(self, question: str) -> str:
        """
        Run the ReAct agent.
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
            if action.startswith("Finish"):
                finish_answer = re.match(r"Finish\[(.*)\]", action).group(1)
                print(f"Final Answer: {finish_answer}")
                return finish_answer

            tool_name, tool_input = self._parse_action(action)
            if not tool_name or not tool_input:
                continue
            print(f"Action: {tool_name} [{tool_input}]")

            tool_function = self.tool_executor.getTool(tool_name)
            if not tool_function:
                observation = f"Error: Tool {tool_name} not found"
            else:
                observation = tool_function(tool_input)
            
            print(f"Observation: {observation}")

            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")
        
        return None

    def _parse_output(self, text: str):
        thought_match = re.search(r"Thought: (.*)", text)
        action_match = re.search(r"Action: (.*)", text)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action
    
    def _parse_action(self, action_text: str):
        match = re.match(r"(\w+)\[(.*)\]", action_text)
        if match:
            return match.group(1), match.group(2)
        else:
            return None, None
    
    def _parse_action_input(self, action_text: str):
        match = re.match(r"(\w+)\[(.*)\]", action_text)
        return match.group(1) if match else ""


if __name__ == '__main__':
    llm = GeneralLLMClient()
    tool_executor = ToolExecutor()
    tool_description = "一个天气查询工具。当你需要回答某个地区的天气时，应使用此工具。"
    tool_executor.registerTool("get_weather", tool_description, get_weather)
    agent = ReActAgent(llm_client=llm, tool_executor=tool_executor)
    question = "今天广州天气怎么样，我要去旅游"
    result = agent.run(question)
    print(f"Result: {result}")