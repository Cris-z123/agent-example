from openai import OpenAI


class OpenAICompatibleClient:
    """
    调用任何兼容OpenAI API的LLM的客户端
    """

    def __init__(
        self, model: str, api_key: str, base_url: str, extra_body: dict | None = None
    ):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        # store default extra body (optional)
        self.extra_body = extra_body or {}

    def generate(
        self, prompt: str, system_prompt: str, extra_body: dict | None = None
    ) -> str:
        """
        调用LLM 接口生成回应

        :param extra_body: 可选的额外请求参数，会与初始化时的 `extra_body` 合并，优先使用方法传入的值
        """
        print("正在调用中...")
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

            # 合并默认 extra_body 与本次调用的 extra_body，调用级别的参数优先
            merged_extra_body = {**self.extra_body, **(extra_body or {})}

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
                extra_body=merged_extra_body,
            )

            answer = response.choices[0].message.content
            print("调用成功")
            return answer
        except Exception as e:
            print(f"调用LLM API时出错: {e}")
            return "抱歉，调用语言模型时出错。"
