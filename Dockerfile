# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

COPY requirements.lock ./
RUN python -m pip install --prefix=/install --no-compile -r requirements.lock


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN groupadd --gid 10001 insightflow \
    && useradd --uid 10001 --gid insightflow --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin insightflow \
    && mkdir -p /app/workspaces /app/reports/charts /app/reports/markdown /app/logs/traces \
    && chown -R insightflow:insightflow /app/workspaces /app/reports /app/logs

COPY --from=builder /install /usr/local

COPY --chown=root:root api ./api
COPY --chown=root:root agents ./agents
COPY --chown=root:root graph ./graph
COPY --chown=root:root llm_ops ./llm_ops
COPY --chown=root:root mcp_servers ./mcp_servers
COPY --chown=root:root observability ./observability
COPY --chown=root:root question_understanding ./question_understanding
COPY --chown=root:root semantic_layer ./semantic_layer
COPY --chown=root:root sql_planning ./sql_planning
COPY --chown=root:root tools ./tools
COPY --chown=root:root visualization ./visualization
COPY --chown=root:root visualization_delivery ./visualization_delivery
COPY --chown=root:root workspaces/*.py ./workspaces/
COPY --chown=root:root data/*.md data/*.yaml data/*.json ./data/

USER insightflow:insightflow

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; exec(\"try:\\n response = urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2)\\nexcept Exception:\\n raise SystemExit(1)\\nraise SystemExit(0 if response.status == 200 else 1)\")"]

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
