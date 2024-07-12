FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04
ARG VERSION=0.5.1
WORKDIR /workspace

ENV ANTHROPIC_API_KEY=""
ENV CLAUDE_PROXY_API_KEY=""
ENV ANTHROPIC_MODEL="claude-3-haiku-20240307"
ENV REQUEST_TIMEOUT=60
ENV MODEL_TEMPERATURE=0.1
ENV TOKENS_PER_MINUTE=10000
ENV REQUESTS_PER_MINUTE=60
ENV MAX_TOKENS=4096

RUN --mount=type=cache,target=/var/cache/apt --mount=type=cache,target=/var/lib/apt \
    apt-get update && \
    apt-get -y --no-install-recommends install \
    python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --no-cache-dir --upgrade pip wheel

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

CMD [ "./entrypoint.sh" ]
