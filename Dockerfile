FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE = 1 \
    PYTHONUNBUFFERED = 1
RUN apt-get update

FROM base AS builder
COPY . .
ENV POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION="1.8.2"
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN <<EOF
set -e
apt-get install --no-install-recommends -y \
  curl \
  build-essential
curl -sSL https://install.python-poetry.org | python3 -
poetry self add poetry-plugin-bundle
poetry bundle venv --only=main /venv
EOF

FROM base AS runner
COPY --from=builder /venv /venv
COPY docker/entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh
RUN apt-get clean
CMD ["/opt/entrypoint.sh"]
