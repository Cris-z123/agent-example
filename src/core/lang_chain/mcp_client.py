import asyncio
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

async def main():
    client = MultiServerMCPClient(
        # {
        #     "math_server": {
        #         "transport": "stdio",
        #         "command": "",
        #         "args": [],
        #     }
        # },
        {
            "weather": {
                "transport": "http",
                "url": "http://localhost:8001/test",
            }
        }
    )

    mcpTools = await client.get_tools()

    glm_llm = init_chat_model(
        model= os.getenv("GLM_MODEL_ID"),
        model_provider="openai",
        base_url= os.getenv("GLM_BASE_URL"),
        api_key= os.getenv("GLM_API_KEY"),
    )

    agent = create_agent(
        model=glm_llm,
        tools=mcpTools,
    )

    weather_response = await agent.ainvoke({"messages": [{"role": "user", "content": "深圳天气怎么样" }]})

    print(f"响应: {weather_response}")
    print(f"天气: {weather_response['messages'][-1].content}")


if __name__ == "__main__":
    asyncio.run(main())
