import os
from typing import Optional


class SearchTool():
    def __init__(self, backend: str = 'hybird', tavily_key: Optional[str] = None, serpapi_key: Optional[str] = None):
        super().__init__(
            name="search",
            description="使用搜索工具进行信息查询，适用于需要获取最新信息的场景。"
        )

        self.backend = backend
        self.tavily_key = tavily_key or os.getenv("TAVILY_KEY")
        self.serpapi_key = serpapi_key or os.getenv("SERPAPI_API_KEY")
        self.available_backends = []
        self._setup_backends()

    def _search_hybird(self, query: str) -> str:
        if "tavily" in self.available_backends:
            try:
                return self._search_tavily(query)
            except Exception as e:
                print(f"Error occurred while searching with Tavily: {e}")
                if "serpapi" in self.available_backends:
                        return self._search_serpapi(query)
        elif "serpapi" in self.available_backends:
            try:
                return self._search_serpapi(query)
            except Exception as e:
                print(f"Error occurred while searching with SerpAPI: {e}")
        else:
            return "没有可用的搜索后端，请检查配置。"

        return "搜索失败，所有后端均不可用。"

    def _search_tavily(self, query: str) -> str:
        response = self.tavily_client.search(query, search_depth="basic", include_answer=True, max_results=3)

        result = f"Tavily搜索结果:{response.get('answer', '未找到答案') }:\n"

        for i, item in enumerate(response.get('results', [])[:3], 1):
            result += f"{i}. {item.get('title', '')}\n"
            result += f"   {item.get('content', '')[:200]}...\n"
            result += f"   来源: {item.get('url', '')}\n\n"

        return result
