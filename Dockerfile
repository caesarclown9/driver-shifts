# Client build: static files only, discarded after the copy below.
FROM node:22.20-alpine AS web
WORKDIR /web
RUN corepack enable
COPY web/package.json web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
RUN pnpm build

FROM python:3.13-slim AS app
COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /srv/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/app ./app
COPY data /srv/data
COPY --from=web /web/dist /srv/web

RUN useradd --system --uid 10001 driver && mkdir -p /srv/var && chown driver /srv/var
USER driver

ENV PATH=/opt/venv/bin:$PATH \
    DS_DB_PATH=/srv/var/trips.db \
    DS_SEED_PATH=/srv/data/trips.json \
    DS_STATIC_DIR=/srv/web
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/days')"
CMD ["uvicorn", "--factory", "app.main:create_app", "--host", "0.0.0.0", "--port", "8000"]
