import re
from typing import Iterator, Optional

from .agentBase import AgentBase
from .config import Config
from .generalLLMClient import GeneralLLMClient
from .message import Message


class MySimpleAgent(AgentBase):
    def __init__(
            self,
            name: str,
            llm: GeneralLLMClient,
            system_prompt: Optional[str] = None,
            config: Optional[Config] = None,
            tool_registry: Optional['ToolRegistry'] = None,
            enable_tool_calls: bool = True
        ):
        super().__init__(name, llm, system_prompt, config)
        self.tool_registry = tool_registry
        self.enable_tool_calls = enable_tool_calls and tool_registry is not None
        print(f"{name} 初始化完成，工具调用：{'启用' if self.enable_tool_calls else '禁用'}")

    def run(self, input_text: str, max_tool_iterations: int = 3, **kwargs) -> str:
        print(f"{self.name} 收到输入: {input_text}")

        messages = []

        enhanced_system_prompt = self.system_prompt or ""
        messages.append({"role": "system", "content": enhanced_system_prompt})

        for msg in self.get_history():
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": input_text})

        if not self.enable_tool_calls:
            response = self.llm.invoke(
                messages=messages,
                **kwargs
            )
            self.add_message(Message(role="user", content=input_text))
            self.add_message(Message(role="assistant", content=response))
            print(f"{self.name} 生成回应: {response}")
            return response

        return self._run_with_tools(messages, input_text, max_tool_iterations, **kwargs)

    def _get_enhanced_system_prompt(self) -> str:
        base_prompt = self.system_prompt or "你是一个AI助手，能够使用工具来帮助用户完成任务。"

        if not self.enable_tool_calls or not self.tool_registry:
            return base_prompt
        tools_description = self.tool_registry.get_tools_description()
        if not tools_description or tools_description == "暂无可用工具":
            return base_prompt

        tools_section = "\n\n可用工具:\n"
        tools_section += "\n\n当你可以使用以下工具来处理或回答问题:\n"
        tools_section += tools_description + "\n"

        tools_section += "\n## 工具调用格式：\n"
        tools_section += "当需要使用工具时，请使用以下格式"
        tools_section += "`[TOOL_CALL:{tool_name}:{parameters}]`\n"
        tools_section += "\n例如: `[TOOL_CALL:search:Python编程]` 或 `[TOOL_CALL:memory:recall=用户信息]`\n"
        tools_section += "工具调用结果会自动插入到后续的对话中，然后你可以基于结果继续回答。"

        return base_prompt + tools_section

    def _run_with_tools(self, messages: list, input_text: str, max_tool_iterations: int, **kwargs) -> str:
        current_iteration = 0
        final_response = ""

        while current_iteration < max_tool_iterations:
            response = self.llm.invoke(messages, **kwargs)

            tool_calls = self._parse_tool_calls(response)

            if tool_calls:
                print(f"{self.name} 识别到工具调用: {tool_calls}")
                tool_results = []
                clean_response = response

                for call in tool_calls:
                    result = self._execute_tool_call(call['tool_name'], call['parameters'])
                    tool_results.append(result)
                    clean_response = clean_response.replace(call['original'], "")

                messages.append({"role": "assistant", "content": clean_response})

                tool_results_text = "\n\n".join(tool_results)
                messages.append({"role": "tool", "content": f"工具执行结果: \n{tool_results_text}\n\n请基于这些结果继续回答用户的问题。"})

                current_iteration += 1

                continue

            final_response = response
            break
        if current_iteration >= max_tool_iterations and not final_response:
            final_response = self.llm.invoke(messages, **kwargs)

        self.add_message(Message(role="user", content=input_text))
        self.add_message(Message(role="assistant", content=final_response))
        print(f"{self.name} 响应完成")

        return final_response

    def _parse_tool_calls(self, text: str) -> list:

        pattern = r'\[TOOL_CALL:([^:]+):([^\]]+)\]'
        matches = re.findall(pattern, text)

        tools_calls = []

        for tool_name, parameters in matches:
            tools_calls.append({
                "tool_name": tool_name.strip(),
                "parameters": parameters.strip(),
                "original": f"[TOOL_CALL:{tool_name}:{parameters}]"
            })
        return tools_calls

    def _execute_tool_call(self, tool_name: str, parameters: str) -> str:
        if not self.tool_registry:
            return "工具调用失败: 没有工具注册表"

        try:
            if tool_name == 'calculator':
                result = self.tool_registry.execute_tool(tool_name, parameters)
            else:
                param_dict = self._parse_tool_parameters(tool_name, parameters)
                tool = self.tool_registry.get_tool(tool_name)
                if not tool:
                    return f"工具调用失败: 未找到工具 '{tool_name}'"
                result = tool.run(param_dict)
            return f"工具 '{tool_name}' 执行结果: \n{result}"
        except Exception as e:
            return f"工具调用 '{tool_name}' 失败: {e}"

    def _parse_tool_parameters(self, tool_name: str, parameters: str) -> dict:

        param_dict = {}

        if '=' in parameters:
            if ',' in parameters:
                pairs = parameters.split(',')
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        param_dict[key.strip()] = value.strip()
            else:
                key, value = parameters.split('=', 1)
                param_dict[key.strip()] = value.strip()
        else:
            if tool_name == 'search':
                param_dict = {'query': parameters}
            elif tool_name == 'memory':
                param_dict = {'action': 'search', 'query': parameters}
            else:
                param_dict = {'input': parameters}

        return param_dict

    def stream_run(self, input_text: str, **kwargs) -> Iterator[str]:
        messages = []

        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        for msg in self.get_history():
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": input_text})

        full_response = ""
        for chunk in self.llm.stream_invoke(messages, **kwargs):
            full_response += chunk
            yield chunk

        print()

        self.add_message(Message(role="user", content=input_text))
        self.add_message(Message(role="assistant", content=full_response))
        print(f"{self.name} 流式响应完成")

    def add_tool(self, tool) -> None:
        if not self.tool_registry:
            print("无法添加工具: 没有工具注册表")
            return
        self.tool_registry.register_tool(tool)
        print(f"工具 '{tool.name}' 已添加")

    def has_tool(self) -> bool:
        return self.enable_tool_calls and self.tool_registry is not None

    def remove_tool(self, tool_name: str) -> bool:
        if self.tool_registry:
            self.tool_registry.unregister(tool_name)
            return True
        return False

    def list_tools(self) -> list:
        if self.tool_registry:
            return self.tool_registry.list_tools()
        return []
