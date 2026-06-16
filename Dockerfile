FROM python:3.12-slim AS build

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

FROM python:3.12-slim
WORKDIR /app
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin /usr/local/bin
COPY src ./src

ENV PYTHONUNBUFFERED=1 \
    MCP_TRANSPORT=sse \
    HTTP_PORT=8080
EXPOSE 8080
ENV PYTHONPATH=/app/src
CMD ["python", "-m", "agentic_rag_mcp"]
