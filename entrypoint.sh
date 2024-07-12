#!/usr/bin/env bash

set -x

# Function to check environment variables
check_env_var() {
  var_name="$1"
  if [ -z "${!var_name}" ]; then
    echo "Error: Environment variable $var_name is not set or is empty."
    exit 1
  fi
}

# Check required environment variables
check_env_var "CLAUDE_PROXY_API_KEY"
check_env_var "ANTHROPIC_API_KEY"
check_env_var "ANTHROPIC_MODEL"
check_env_var "REQUEST_TIMEOUT"
check_env_var "MODEL_TEMPERATURE"
check_env_var "TOKENS_PER_MINUTE"
check_env_var "REQUESTS_PER_MINUTE"
check_env_var "MAX_TOKENS"

# Proceed with the rest of the script if all checks pass
echo "All required environment variables are set."

# Set default port to 8000 if PORT is not set
PORT="${PORT:-8000}"

uvicorn server-openai:app --host 0.0.0.0 --port $PORT
