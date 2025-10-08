FROM debian:trixie-slim
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /uvx /bin/

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install ccache build-essential tesseract-ocr ffmpeg libsm6 libxext6 default-jdk --no-install-recommends -y \
    && rm -rf /var/lib/apt/lists/* \
    && tesseract -v

WORKDIR /app

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/uv to speed up subsequent builds.

# Copy the lockfile and `pyproject.toml` into the image
COPY uv.lock pyproject.toml .python-version /app/
ENV UV_CACHE_DIR=/root/.cache/uv
ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-project --no-dev

ENV PATH=/app/.venv/bin:$PATH

RUN uv pip install pip
RUN uv run python -m spacy download en_core_web_lg

# Copy the project into the image
COPY . .

## Bootstrap PaddleOCR to include the configured models:
RUN uv run python -c 'from paddle_ocr import PresidioPaddleOCR; PresidioPaddleOCR(config_file="PaddleOCR.yaml")'

# RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Run the application
ENTRYPOINT ["uv", "run", "python", "main.py"]
