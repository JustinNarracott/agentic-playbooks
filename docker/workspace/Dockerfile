FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y \
    git \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python deps
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    ruff \
    mypy \
    pydantic \
    httpx \
    sqlalchemy \
    psycopg2-binary \
    pyyaml \
    jinja2 \
    openai \
    anthropic

# Working directory
WORKDIR /workspace

# Keep container running
CMD ["tail", "-f", "/dev/null"]
