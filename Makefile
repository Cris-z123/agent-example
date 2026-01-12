.PHONY: sync dev format clean

sync:
    uv sync --group dev

format:
    uv run ruff check . --fix
    uv run black .

clean:
    rm -rf .venv
    find . -type d -name "__pycache__" -exec rm -rf {} +