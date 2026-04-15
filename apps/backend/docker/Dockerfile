FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy the application into the container.
COPY . /app

# Install the application dependencies.
WORKDIR /app
RUN uv sync --frozen --no-cache

# Create storage directories
RUN mkdir -p /app/storage/books

# Make entrypoint executable
RUN chmod +x /app/docker/entrypoint.sh

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /app/.venv/bin/python -c "import httpx; httpx.get('http://localhost:8678/health', timeout=5)" || exit 1

# Run the application via entrypoint
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["/app/.venv/bin/fastapi", "run", "src/main.py", "--port", "8678", "--host", "0.0.0.0"]
