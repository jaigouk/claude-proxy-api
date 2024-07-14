FROM python:3.10.14-slim-bookworm

WORKDIR /workspace

ENV ANTHROPIC_API_KEY=""
ENV CLAUDE_PROXY_API_KEY=""
ENV ANTHROPIC_MODEL="claude-3-haiku-20240307"
ENV REQUEST_TIMEOUT=60
ENV MODEL_TEMPERATURE=0.1
ENV TOKENS_PER_MINUTE=10000
ENV REQUESTS_PER_MINUTE=60
ENV MAX_TOKENS=4096

# Use a single RUN command to update, install, and clean up in one layer to keep the image size down
RUN --mount=type=cache,target=/var/cache/apt --mount=type=cache,target=/var/lib/apt \
    apt-get update && \
    apt-get -y --no-install-recommends install python3 python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Ensure pip is upgraded using python3 explicitly
RUN python3 -m pip install --no-cache-dir --upgrade pip wheel

COPY requirements.txt .

# Use python3 explicitly to ensure consistency
RUN python3 -m pip install -r requirements.txt

COPY . .

CMD [ "./entrypoint.sh" ]
