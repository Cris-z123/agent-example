import os


class AdvanceSearchTool:
    def __init__(self):
        self.name  = "advance_search"
        self.description = "使用高级搜索工具进行信息查询，适用于需要获取最新信息的场景。"
        self.search_source = []
        self._setup_search_sources()

    def _setup_search_sources(self):
        if os.getenv("TAVILY_API_KEY"):
            try:
                from tavily import TavilyClient
                self.tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
                self.search_source.append("tavily")
                print("Tavily搜索后端已启用")
            except ImportError:
                print("未安装tavily库，无法使用Tavily搜索后端")

        if os.getenv("SERPAPI_API_KEY"):
            try:
                import serpapi
                self.search_source.append("serpapi")
                print("Google Search搜索后端已启用")
            except ImportError:
                print("未安装serpapi库")

        if self.search_source:
            print(f"已启用的搜索后端: {', '.join(self.search_source)}")
        else:
            print("没有可用的搜索后端，请配置API密钥。")

    def search(self, query: str) -> str:
        if not query.strip():
            return "搜索查询不能为空，请提供有效的查询内容。"

        if not self.search_source:
            return "没有可用的搜索后端，请检查配置。"

        print(f"开始智能搜索：{query}")

        for source in self.search_source:
            try:
                if source == "tavily":
                    result = self._search_with_tavily(query)
                    if result and "未找到" not in result:
                        return f"tavily 搜索结果:\n{result}"
                elif source == "serpapi":
                    result = self._search_with_serpapi(query)
                    if result and "未找到" not in result:
                        return f"serpapi 搜索结果:\n{result}"
            except Exception as e:
                print(f"搜索后端 '{source}' 出现错误: {e}")
                continue
        return "搜索失败，所有后端均不可用或未找到相关结果。"

    def _search_with_tavily(self, query: str) -> str:
        response = self.tavily_client.search(query=query,  max_results=3)

        if response.get('answer'):
            result = f"Tavily搜索结果: {response.get('answer')}\n\n"
        else:
            result = ""

        result += "相关搜索结果:\n"

        for i, item in enumerate(response.get('results', [])[:3], 1):
            result += f"{i}. {item.get('title', '')}\n"
            result += f"   {item.get('content', '')[:150]}...\n"

        return result

    def _search_with_serpapi(self, query: str) -> str:
        import serpapi
        search = serpapi.GoogleSearch({
            "q": query,
            "api_key": os.getenv("SERPAPI_API_KEY"),
            "num": 3
        })
        results = search.get_dict()

        result = 'SerpAPI搜索结果:\n'
        for i, res in enumerate(results.get('organic_results', [])[:3], 1):
            result += f"{i}. {res.get('title', '')}\n"
            result += f"   {res.get('snippet', '')}\n\n"

        return result

    def create_advance_search_registry(self):

        registry = ToolRegistry()

        search_tool = AdvanceSearchTool()

        registry.register_function(
            name="advance_search",
            description="使用搜索工具进行信息查询，适用于需要获取最新信息的场景。",
            func=search_tool.search
        )

        return registry
