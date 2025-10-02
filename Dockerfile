FROM debian:trixie-slim
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /uvx /bin/

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install build-essential tesseract-ocr ffmpeg libsm6 libxext6 default-jdk --no-install-recommends -y \
    && rm -rf /var/lib/apt/lists/* \
    && tesseract -v

# Copy the project into the image
ADD . /app

# Sync the project into a new environment, asserting the lockfile is up to date
WORKDIR /app
RUN uv sync --frozen

RUN uv run python -m ensurepip

RUN uv run python -m spacy download en_core_web_lg

COPY . /app
WORKDIR /app

# Run the application
ENTRYPOINT ["/bin/uv", "run", "python", "main.py"]
