FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Copy the application into the container.
COPY . /app

# Install the application dependencies.
WORKDIR /app
RUN uv sync --frozen --no-cache

# Run the application.
CMD ["/app/.venv/bin/fastapi", "run", "src/main.py", "--port", "8678", "--host", "0.0.0.0"]
