FROM rust:1-bookworm AS blitz-builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends libfontconfig1-dev libfreetype-dev \
    && rm -rf /var/lib/apt/lists/*

ENV UV_PYTHON_DOWNLOADS=automatic \
    UV_PYTHON=3.13

WORKDIR /build

COPY blitz_render ./blitz_render
# runtime image installs fontconfig/freetype, so no need to vendor them into the wheel
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/build/blitz_render/target \
    uvx maturin build --release --auditwheel skip --manifest-path blitz_render/Cargo.toml --out /wheels


FROM python:3.13-slim-bookworm

# blitz needs fontconfig/freetype at runtime, plus the fonts our templates name explicitly
# (text + color emoji) and a CJK fallback
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libfontconfig1 \
        libfreetype6 \
        fonts-liberation \
        fonts-noto-color-emoji \
        fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/*

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=3.13 \
    PATH="/app/.venv/bin:$PATH" \
    IMAGE_RENDERER=blitz

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY blitz_render/pyproject.toml ./blitz_render/pyproject.toml
# uv binary and its cache are only mounted at build time, keeping both out of the image
RUN --mount=from=ghcr.io/astral-sh/uv:latest,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra server --no-dev --no-install-project

COPY x_twitter_thread_dump ./x_twitter_thread_dump
RUN --mount=from=ghcr.io/astral-sh/uv:latest,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra server --no-dev

# prebuilt in the rust stage, so the final image doesn't need a rust toolchain
# (installed after the last `uv sync`, which would otherwise remove it)
RUN --mount=from=ghcr.io/astral-sh/uv:latest,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=from=blitz-builder,source=/wheels,target=/tmp/wheels \
    uv pip install --no-deps /tmp/wheels/*.whl

CMD ["uvicorn", \
     "--proxy-headers", \
     "--forwarded-allow-ips=*", \
     "--host=0.0.0.0", \
     "--port=8000", \
     "--no-access-log", \
     "x_twitter_thread_dump._api:app"]
