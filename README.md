# Agent Example

一个智能体（Agent）开发示例项目，展示了如何构建能够使用工具进行推理和行动的智能助手系统。

## 功能特性

- 🤖 **多种智能体实现**：支持 ReAct、Plan-and-Solve、Reflection 等多种智能体模式
- 🔧 **工具系统**：内置计算器和天气查询等工具，支持自定义工具扩展
- 🌐 **多 LLM 提供商支持**：支持 OpenAI、DeepSeek、Qwen、ModelScope、Kimi、智谱、Ollama、vLLM 等多种 LLM 服务
- 🔄 **流式响应**：支持 LLM 流式输出，提供更好的交互体验
- 📦 **模块化设计**：清晰的代码结构，易于扩展和维护

## 项目结构

```
agent-example/
├── src/
│   ├── core/                    # 核心模块
│   │   ├── GeneralLLMClient.py      # 通用 LLM 客户端
│   │   ├── CustomizationLLM.py      # 多提供商 LLM 客户端
│   │   └── OpenAICompatibleClient.py # OpenAI 兼容客户端
│   ├── tools/                   # 工具模块
│   │   ├── calculator.py            # 数学计算工具
│   │   ├── get_weather.py          # 天气查询工具
│   │   ├── tool_executor.py        # 工具执行器
│   │   └── tool_definitions.py     # 工具定义映射
│   ├── knowledge/               # 智能体实现
│   │   ├── ReActAgent.py           # ReAct 智能体（推理+行动）
│   │   ├── PlanAndSolveAgent.py    # 规划求解智能体
│   │   ├── ReflectionAgent.py      # 反思智能体
│   │   └── Transformer.py          # Transformer 相关实现
│   └── main.py                  # 主程序入口
├── pyproject.toml              # 项目配置和依赖
├── uv.lock                     # 依赖锁定文件
├── Makefile                    # 构建脚本
└── README.md                   # 项目文档
```

## 环境要求

- **Python**: >= 3.12
- **包管理器**: [uv](https://github.com/astral-sh/uv) (推荐) 或 pip
- **LLM API**: 需要配置至少一个 LLM 服务的 API 密钥

## 安装步骤

### 1. 克隆项目

```bash
git clone <repository-url>
cd agent-example
```

### 2. 安装依赖

使用 `uv`（推荐）：

```bash
# 安装 uv（如果尚未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 同步依赖
make sync
# 或直接运行
uv sync --group dev
```

使用 `pip`：

```bash
pip install -e .
pip install -e ".[dev]"  # 包含开发依赖
```

### 3. 配置环境变量

创建 `.env` 文件并配置 LLM API 密钥：

```bash
# 通用配置（CustomizationLLM 使用）
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.example.com/v1
MODEL_SCOPE_MODEL_ID=your_model_id

# 或使用特定提供商配置
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=...
DASHSCOPE_API_KEY=...        # Qwen
MODELSCOPE_API_KEY=...       # ModelScope
KIMI_API_KEY=...             # Kimi/Moonshot
ZHIPU_API_KEY=...            # 智谱AI
OLLAMA_HOST=http://localhost:11434
VLLM_HOST=http://localhost:8000

# 超时设置
LLM_TIMEOUT=60


## 开发指南

### 代码格式化

```bash
# 使用 Makefile
make format

# 或手动运行
uv run ruff check . --fix
uv run black .
```

## 代码规范

- 遵循 PEP 8 代码风格
- 使用 `ruff` 进行代码检查，使用 `black` 进行格式化
