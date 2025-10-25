# ===============================
# === Device Type Arguments ====
# ===============================
ARG USE_CUDA=false
ARG USE_OLLAMA=false 
ARG USE_SLIM=false
ARG USE_CUDA_VER=""
ARG USE_EMBEDDING_MODEL=""
ARG USE_RERANKING_MODEL=""
ARG USE_TIKTOKEN_ENCODING_NAME="cl100k_base"
ARG BUILD_HASH=dev-build
ARG UID=0
ARG GID=0


# ===============================
# === Frontend (WebUI) Build ===
# ===============================
FROM --platform=$BUILDPLATFORM node:22-alpine3.20 AS build
ARG BUILD_HASH

WORKDIR /app

RUN apk add --no-cache git

COPY package.json package-lock.json ./
RUN npm ci --force

COPY . .

# ✅ Increase Node.js memory limit BEFORE build
ENV NODE_OPTIONS="--max-old-space-size=8192"
ENV APP_BUILD_HASH=${BUILD_HASH}

RUN npm run build


# ===============================
# === Backend (Python API) =====
# ===============================
FROM python:3.11-slim-bookworm AS base

# ---- Build Args ----
ARG USE_CUDA
ARG USE_OLLAMA
ARG USE_CUDA_VER
ARG USE_SLIM
ARG USE_EMBEDDING_MODEL
ARG USE_RERANKING_MODEL
ARG UID
ARG GID

# ---- Environment Setup ----
ENV ENV=prod \
    PORT=8080 \
    USE_CUDA_DOCKER=${USE_CUDA} \
    USE_SLIM_DOCKER=${USE_SLIM} \
    USE_CUDA_DOCKER_VER=${USE_CUDA_VER} \
    USE_EMBEDDING_MODEL_DOCKER=${USE_EMBEDDING_MODEL} \
    USE_RERANKING_MODEL_DOCKER=${USE_RERANKING_MODEL}

# ---- API Key / Config Defaults ----
ENV OLLAMA_BASE_URL="" \
    OPENAI_API_KEY="" \
    WEBUI_SECRET_KEY="" \
    SCARF_NO_ANALYTICS=true \
    DO_NOT_TRACK=true \
    ANONYMIZED_TELEMETRY=false

# ---- Other Model Configs ----

ENV RAG_EMBEDDING_MODEL="$USE_EMBEDDING_MODEL_DOCKER" \
    RAG_RERANKING_MODEL="$USE_RERANKING_MODEL_DOCKER" \
    SENTENCE_TRANSFORMERS_HOME="/app/backend/data/cache/embedding/models"

ENV TIKTOKEN_ENCODING_NAME="cl100k_base" \
    TIKTOKEN_CACHE_DIR="/app/backend/data/cache/tiktoken"

ENV HF_HOME="/app/backend/data/cache/embedding/models"

WORKDIR /app/backend
ENV HOME=/root

# ---- Create Non-Root User (if specified) ----
RUN if [ "$UID" -ne 0 ]; then \
      if [ "$GID" -ne 0 ]; then \
        addgroup --gid "$GID" app; \
      fi; \
      adduser --uid "$UID" --gid "$GID" --home "$HOME" --disabled-password --no-create-home app; \
    fi

# ---- Prepare cache ----
RUN mkdir -p $HOME/.cache/chroma && \
    echo -n 00000000-0000-0000-0000-000000000000 > $HOME/.cache/chroma/telemetry_user_id && \
    chown -R $UID:$GID /app $HOME

# ---- Install dependencies ----
COPY ./backend/deb-packages /deb-packages
RUN dpkg -i /deb-packages/*.deb || apt-get install -f -y && \
    rm -rf /var/lib/apt/lists/*

# ---- Copy requirements and local packages ----
COPY --chown=$UID:$GID ./backend/requirements.txt ./requirements.txt
COPY --chown=$UID:$GID ./backend/packages ./packages


# ---- Install Python packages ----
RUN pip install --no-cache-dir uv && \
    pip install --no-cache-dir --find-links ./packages -r requirements.txt || \
    (pip download --dest ./packages -r requirements.txt && \
     pip install --no-cache-dir --find-links ./packages -r requirements.txt) && \
    mkdir -p /app/backend/data && chown -R $UID:$GID /app/backend/data/

# ---- Copy frontend build from Node stage ----
COPY --chown=$UID:$GID --from=build /app/build /app/build
COPY --chown=$UID:$GID --from=build /app/CHANGELOG.md /app/CHANGELOG.md
COPY --chown=$UID:$GID --from=build /app/package.json /app/package.json

COPY --chown=$UID:$GID ./backend .

EXPOSE 8080

HEALTHCHECK CMD curl --silent --fail http://localhost:${PORT:-8080}/health | jq -ne 'input.status == true' || exit 1

RUN set -eux; \
    chgrp -R 0 /app /root || true; \
    chmod -R g+rwX /app /root || true; \
    find /app -type d -exec chmod g+s {} + || true; \
    find /root -type d -exec chmod g+s {} + || true

USER $UID:$GID

ARG BUILD_HASH
ENV WEBUI_BUILD_VERSION=${BUILD_HASH}
ENV DOCKER=true

CMD ["bash", "start.sh"]
