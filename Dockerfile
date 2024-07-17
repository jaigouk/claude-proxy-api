# Use a multi-arch base image
FROM --platform=$BUILDPLATFORM python:3.10.14-slim-bookworm as builder

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Final stage
FROM --platform=$TARGETPLATFORM python:3.10.14-slim-bookworm

WORKDIR /app

# Copy installed dependencies and source code
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /app /app

# Set default environment variables
ENV ANTHROPIC_API_KEY="mock_anthropic_api_key" \
    CLAUDE_PROXY_API_KEY="mock_claude_proxy_api_key" \
    ANTHROPIC_MODEL="claude-3-haiku-20240307" \
    REQUEST_TIMEOUT=60 \
    MODEL_TEMPERATURE=0.1 \
    TOKENS_PER_MINUTE=10000 \
    REQUESTS_PER_MINUTE=60 \
    MAX_TOKENS=4096

# Run the application
CMD ["./entrypoint.sh"]
