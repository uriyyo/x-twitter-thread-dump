FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=automatic \
    UV_PYTHON=3.13 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --extra server --no-dev --no-install-project

COPY x_twitter_thread_dump ./x_twitter_thread_dump
RUN uv sync --frozen --extra server --no-dev

RUN uv run playwright install --with-deps chrome

CMD ["uvicorn", \
     "--proxy-headers", \
     "--forwarded-allow-ips=*", \
     "--host=0.0.0.0", \
     "--port=8000", \
     "--no-access-log", \
     "x_twitter_thread_dump._api:app"]
