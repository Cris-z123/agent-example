import os
from typing import Literal, Optional

from GeneralLLMClient import GeneralLLMClient

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

class CustomizationLLM(GeneralLLMClient):
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
                elif "api.deepseel.com" in base_url_lower:
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
                resolved_base_url = base_url or os.getenv('LLM_BASE_URL') or 'https://api.deepseel.com'
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
