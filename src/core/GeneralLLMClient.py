import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()

class GeneralLLMClient: 
    def __init__(self, model: str = None, api_key: str = None, base_url: str = None, timeout: int = None, extra_body: Optional[Dict] = None):
        """
        初始化客户端。优先使用传入参数，如果未提供，则从环境变量加载。
        
        Args:
            model: 模型ID
            api_key: API密钥
            base_url: API基础URL
            timeout: 请求超时时间（秒）
            extra_body: 额外的请求体参数，将传递给模型创建调用
        """
        self.model = model or os.getenv('ALICS_MODEL_ID')
        api_key = api_key or os.getenv('ALICS_API_KEY')
        base_url = base_url or os.getenv("ALICS_BASE_URL")
        timeout = timeout or int(os.getenv("LLM_TIMEOUT", 60))

        if not all([self.model, api_key, base_url]):
            raise ValueError('model、api_key and base_url must be submitted or defined in .env')
        
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self.extra_body = extra_body

    def think(self, messages: List[Dict[str, str]], temperature: float = 0) -> str:
        """
        调用LLM模型进行思考并返回响应。
        
        Args:
            messages: 消息列表
            temperature: 温度参数，控制输出的随机性
            
        Returns:
            模型响应文本，如果发生错误则返回None
        """
        print(f"🧠正在调用{self.model}模型")
        try:
            create_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "stream": True
            }
            if self.extra_body:
                create_params["extra_body"] = self.extra_body
            
            response = self.client.chat.completions.create(**create_params)

            # 处理流式响应
            print("LLM response success")
            collected_content = []
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                collected_content.append(content)
            print() # 流式输出结束后换行
            return "".join(collected_content)
        except Exception as e:
            print(f"❌调用LLM 发生错误：{e}")
            return None
        
if __name__ == '__main__':
    try:
        llm = GeneralLLMClient(extra_body={"enable_search": True})

        example_message = [
            {"role": "system", "content": "You are a helpful assistant that writes Python code."},
            {"role": "user", "content": "查询一下广州最新入户政策"}
        ]

        print("--- 调用LLM ---")
        response_text = llm.think(example_message)
        if response_text:
            print("\n\n--- 完整模型响应 ---")
            print(response_text)

    except ValueError as e:
        print(e)