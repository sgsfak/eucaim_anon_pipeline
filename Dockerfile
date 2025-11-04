# syntax=docker/dockerfile:1.19.0
FROM debian:trixie-slim
LABEL org.opencontainers.image.description="LETHE Dicom Anonymization pipeline"
LABEL org.opencontainers.image.licenses=EUPL-1.2

COPY --from=ghcr.io/astral-sh/uv:0.9.3 /uv /uvx /bin/

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
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev --no-editable

ENV PATH=/app/.venv/bin:$PATH
# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Copy the project into the image
COPY . /app

## Bootstrap PaddleOCR to include the configured models:
RUN uv run python -c 'from lethe.paddle_ocr import PresidioPaddleOCR; PresidioPaddleOCR(config_file="PaddleOCR.yaml")'

# Run the application
ENTRYPOINT ["python", "-m", "lethe"]
