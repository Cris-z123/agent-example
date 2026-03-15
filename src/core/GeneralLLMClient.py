import os
from collections.abc import Iterator
from typing import Dict, List, Literal, Optional

from dotenv import load_dotenv
from openai import OpenAI

SUPPORTED_PROVIDERS = Literal[
    "openai",
    "deepseek",
    "qwen",
    "modelscope",
    "kimi",
    "zhipu",
    "ollama",
    "vllm",
    "local",
    "auto",
    "custom",
]

load_dotenv()

class GeneralLLMClient:
    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: Optional[SUPPORTED_PROVIDERS] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        **kwargs
    ):
        self.model = model or os.getenv('MODEL_SCOPE_MODEL_ID')
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout or int(os.getenv('LLM_TIMEOUT', '60'))
        self.kwargs = kwargs
        self.extra_body = kwargs.get('extra_body')

        request_provider = (provider or "").lower() if provider else None
        self.provider = provider or self._auto_detect_provider(api_key, base_url)

        if request_provider == 'custom':
            self.provider = 'custom'
            self.api_key = api_key or os.getenv('LLM_API_KEY')
            self.base_url = base_url or os.getenv('LLM_BASE_URL')
        else:
            self.api_key, self.base_url = self._resolve_credentials(api_key, base_url)

        if not self.model:
            self.model = self._get_default_model()
        if not all([self.api_key, self.base_url]):
            raise ValueError("API key and base URL are required for the selected provider.")
        self.client = self._create_client()

    def _auto_detect_provider(self, api_key: Optional[str], base_url: Optional[str]) -> str:
            if os.getenv('OPENAI_API_KEY'):
                return 'openai'
            elif os.getenv('DEEPSEEK_API_KEY'):
                return 'deepseek'
            elif os.getenv('DASHSCOPE_API_KEY'):
                return 'qwen'
            elif os.getenv('MODELSCOPE_API_KEY'):
                return 'modelscope'
            elif os.getenv('KIMI_API_KEY') or os.getenv('MOONSHOT_API_KEY'):
                return 'kimi'
            elif os.getenv('ZHIPU_API_KEY') or os.getenv('GLM_API_KEY'):
                return 'zhipu'
            elif os.getenv('OLLAMA_API_KEY') or os.getenv('OLLAMA_HOST'):
                return 'ollama'
            elif os.getenv('VLLM_API_KEY') or os.getenv('VLLM_HOST'):
                return 'vllm'

            actual_api_key = api_key or os.getenv('LLM_API_KEY')
            if actual_api_key:
                actual_key_lower = actual_api_key.lower()
                if actual_key_lower.startswith('ms-'):
                    return 'modelscope'
                elif actual_key_lower == 'ollama':
                    return 'ollama'
                elif actual_key_lower == 'vllm':
                    return 'vllm'
                elif actual_key_lower == 'local':
                    return 'local'
                elif actual_api_key.startswith('sk-') and len(actual_api_key) > 50:
                    pass
                elif actual_api_key.endswith(".") or  "." in actual_api_key[-20]:
                    return "zhipu"
            actual_base_url = base_url or os.getenv('LLM_BASE_URL')
            if actual_base_url:
                base_url_lower = actual_base_url.lower()
                if "api.openai.com" in base_url_lower:
                    return "openai"
                elif "api.deepseek.com" in base_url_lower:
                    return "deepseek"
                elif "dashscope.aliyuncs.com" in base_url_lower:
                    return "qwen"
                elif "api-inference.modelscope.cn" in base_url_lower:
                    return "modelscope"
                elif "api.moonshot.cn" in base_url_lower:
                    return "kimi"
                elif "open.bigmodel.cn" in base_url_lower:
                    return "zhipu"
                elif "localhost" in base_url_lower or "127.0.0.1" in base_url_lower:
                    if ":11434" in base_url_lower or  "ollama" in base_url_lower:
                        return "ollama"
                    elif ":8000" in base_url_lower or "vllm" in base_url_lower:
                        return "vllm"
                    elif ":8000" in base_url_lower or ":7860" in base_url_lower:
                        return "local"
                    else:
                        if actual_api_key and actual_api_key.lower() == "ollama":
                            return "ollama"
                        elif actual_api_key and actual_api_key.lower() == "vllm":
                            return "vllm"
                        else:
                            return "local"
                elif any(port in base_url_lower for port in [":8080", ":7860", ":5000"]):
                    return "local"
            return "auto"

    def _resolve_credentials(self, api_key: Optional[str], base_url: Optional[str]) -> tuple[str, str]:
            if self.provider == 'openai':
                resolved_api_key = api_key or os.getenv('OPENAI_API_KEY') or os.getenv("LLM_API_KEY")
                resolved_base_url = base_url or os.getenv('LLM_BASE_URL') or 'https://api.openai.com/v1'
                return resolved_api_key, resolved_base_url
            elif self.provider == 'deepseek':
                resolved_api_key = api_key or os.getenv('DEEPSEEK_API_KEY') or os.getenv("LLM_API_KEY")
                resolved_base_url = base_url or os.getenv('LLM_BASE_URL') or 'https://api.deepseek.com'
                return resolved_api_key, resolved_base_url
            elif self.provider == 'qwen':
                resolved_api_key = api_key or os.getenv('DASHSCOPE_API_KEY') or os.getenv("LLM_API_KEY")
                resolved_base_url = base_url or os.getenv('LLM_BASE_URL') or 'https://dashscope.aliyuncs.com/compatible-mode/v1'
                return resolved_api_key, resolved_base_url
            elif self.provider == 'modelscope':
                resolved_api_key = api_key or os.getenv('MODELSCOPE_API_KEY') or os.getenv("LLM_API_KEY")
                resolved_base_url = base_url or os.getenv('LLM_BASE_URL') or 'https://api-inference.modelscope.cn/v1/'
                return resolved_api_key, resolved_base_url
            elif self.provider == 'kimi':
                resolved_api_key = api_key or os.getenv('KIMI_API_KEY') or os.getenv("MOONSHOT_API_KEY") or os.getenv("LLM_API_KEY")
                resolved_base_url = base_url or os.getenv('LLM_BASE_URL') or 'https://api.moonshot.cn/v1'
                return resolved_api_key, resolved_base_url
            elif self.provider == 'zhipu':
                resolved_api_key = api_key or os.getenv('ZHIPU_API_KEY') or os.getenv("GLM_API_KEY") or os.getenv("LLM_API_KEY")
                resolved_base_url = base_url or os.getenv('LLM_BASE_URL') or 'https://open.bigmodel.cn/api/paas/v4'
                return resolved_api_key, resolved_base_url
            elif self.provider == 'ollama':
                resolved_api_key = api_key or os.getenv('OLLAMA_API_KEY') or os.getenv("LLM_API_KEY") or 'ollama'
                resolved_base_url = base_url or os.getenv('OLLAMA_HOST') or os.getenv("LLM_BASE_URL") or 'http://localhost:11434/v1'
                return resolved_api_key, resolved_base_url
            elif self.provider == 'vllm':
                resolved_api_key = api_key or os.getenv('VLLM_API_KEY') or os.getenv("LLM_API_KEY") or 'vllm'
                resolved_base_url = base_url or os.getenv('VLLM_HOST') or os.getenv("LLM_BASE_URL") or 'http://localhost:8000/v1'
                return resolved_api_key, resolved_base_url
            elif self.provider == 'local':
                resolved_api_key = api_key or os.getenv('LLM_API_KEY') or 'local'
                resolved_base_url = base_url or os.getenv('LLM_BASE_URL') or 'http://localhost:8000/v1'
                return resolved_api_key, resolved_base_url
            elif self.provider == 'custom':
                resolved_api_key = api_key or os.getenv('LLM_API_KEY')
                resolved_base_url = base_url or os.getenv('LLM_BASE_URL')
                return resolved_api_key, resolved_base_url
            else:
                resolved_api_key = api_key or os.getenv("LLM_API_KEY")
                resolved_base_url = base_url or os.getenv("LLM_BASE_URL")
                return resolved_api_key, resolved_base_url

    def _create_client(self) -> OpenAI:
        """创建OpenAI客户端"""
        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )

    def _get_default_model(self) -> str:
        """获取默认模型"""
        if self.provider == "openai":
            return "gpt-3.5-turbo"
        elif self.provider == "deepseek":
            return "deepseek-chat"
        elif self.provider == "qwen":
            return "qwen-plus"
        elif self.provider == "modelscope":
            return "Qwen/Qwen2.5-72B-Instruct"
        elif self.provider == "kimi":
            return "moonshot-v1-8k"
        elif self.provider == "zhipu":
            return "glm-4"
        elif self.provider == "ollama":
            return "llama3.2"  # Ollama常用模型
        elif self.provider == "vllm":
            return "meta-llama/Llama-2-7b-chat-hf"  # vLLM常用模型
        elif self.provider == "local":
            return "local-model"  # 本地模型占位符
        elif self.provider == "custom":
            return self.model or "gpt-3.5-turbo"
        else:
            # auto或其他情况：根据base_url智能推断默认模型
            base_url = os.getenv("LLM_BASE_URL", "")
            base_url_lower = base_url.lower()
            if "modelscope" in base_url_lower:
                return "Qwen/Qwen2.5-72B-Instruct"
            elif "deepseek" in base_url_lower:
                return "deepseek-chat"
            elif "dashscope" in base_url_lower:
                return "qwen-plus"
            elif "moonshot" in base_url_lower:
                return "moonshot-v1-8k"
            elif "bigmodel" in base_url_lower:
                return "glm-4"
            elif "ollama" in base_url_lower or ":11434" in base_url_lower:
                return "llama3.2"
            elif ":8000" in base_url_lower or "vllm" in base_url_lower:
                return "meta-llama/Llama-2-7b-chat-hf"
            elif "localhost" in base_url_lower or "127.0.0.1" in base_url_lower:
                return "local-model"
            else:
                return "gpt-3.5-turbo"

    def think(self, messages: List[Dict[str, str]], temperature: Optional[float] = None, **kwargs) -> Iterator[str]:
        """
        调用大语言模型进行思考，并返回流式响应。

        这是主要的调用方法，默认使用流式响应以获得更好的用户体验。

        Args:
            messages: 消息列表
            temperature: 温度参数，控制输出的随机性
            **kwargs: 其他参数

        Yields:
            模型响应文本片段（流式输出）
        """
        temperature = temperature if temperature is not None else self.temperature

        try:
            create_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": self.max_tokens,
                "stream": True
            }
            if self.extra_body:
                create_params["extra_body"] = self.extra_body

            # 合并额外的 kwargs
            create_params.update(kwargs)

            response = self.client.chat.completions.create(**create_params)

            # 处理流式响应
            print(f"🧠 正在调用 {self.model} 模型")
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                if content:
                    print(content, end="", flush=True)
                    yield content
            print()  # 流式输出结束后换行
        except Exception as e:
            print(f"❌ 调用LLM发生错误：{e}")
            raise

    def invoke(self, messages: List[Dict[str, str]], temperature: Optional[float] = None, **kwargs) -> str:
        """
        非流式调用LLM，返回完整响应对象。

        Args:
            messages: 消息列表
            temperature: 温度参数，控制输出的随机性
            **kwargs: 其他参数

        Returns:
            模型完整响应文本
        """
        temperature = temperature if temperature is not None else self.temperature

        try:
            create_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": self.max_tokens,
                "stream": False
            }
            if self.extra_body:
                create_params["extra_body"] = self.extra_body

            # 合并额外的 kwargs
            create_params.update(kwargs)

            response = self.client.chat.completions.create(**create_params)
            content = response.choices[0].message.content or ""
            print(f"🧠 {self.model} 响应成功")
            return content
        except Exception as e:
            print(f"❌ 调用LLM发生错误：{e}")
            raise

    def stream_invoke(self, messages: List[Dict[str, str]], temperature: Optional[float] = None, **kwargs) -> Iterator[str]:
        """
        流式调用LLM的别名方法，与think方法功能相同。

        Args:
            messages: 消息列表
            temperature: 温度参数，控制输出的随机性
            **kwargs: 其他参数

        Yields:
            模型响应文本片段（流式输出）
        """
        return self.think(messages, temperature, **kwargs)

if __name__ == '__main__':
    """
    测试 GeneralLLMClient 类的基本功能
    """
    try:
        # 测试初始化
        llm = GeneralLLMClient(extra_body={"enable_search": True})
        print("✓ 初始化成功")
        print(f"  - Provider: {llm.provider}")
        print(f"  - Model: {llm.model}")
        print(f"  - Base URL: {llm.base_url}")
        print(f"  - API Key: {'*' * 10 if llm.api_key else 'None'}")
        print()

        # 测试消息准备
        example_message = [
            {"role": "system", "content": "You are a helpful assistant that writes Python code."},
            {"role": "user", "content": "查询一下广州最新入户政策"}
        ]

        # 调用 think 方法（返回生成器）
        response_generator = llm.think(example_message)

        # 收集所有响应片段
        full_response = ""
        print("\n--- 流式响应 ---")
        try:
            for chunk in response_generator:
                full_response += chunk
        except Exception as e:
            print(f"\n❌ 处理响应时发生错误: {e}")
            raise

        print("\n" + "=" * 60)
        print("--- 完整模型响应 ---")
        print(full_response if full_response else "(无响应内容)")

    except ValueError as e:
        print(f"❌ 配置错误: {e}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
