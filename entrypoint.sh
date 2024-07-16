#!/usr/bin/env bash

# Function to check environment variables
check_env_var() {
    var_name="$1"
    default_value="$2"
    if [ -z "$(eval echo \$$var_name)" ]; then
        if [ -n "$default_value" ]; then
            eval export $var_name="$default_value"
            echo "Warning: Environment variable $var_name is not set. Using default value: $default_value"
        else
            echo "Error: Environment variable $var_name is not set or is empty."
            exit 1
        fi
    fi
}

# Check required environment variables
check_env_var "CLAUDE_PROXY_API_KEY" "mock_claude_proxy_api_key"
check_env_var "ANTHROPIC_API_KEY" "mock_anthropic_api_key"
check_env_var "ANTHROPIC_MODEL" "claude-3-haiku-20240307"
check_env_var "REQUEST_TIMEOUT" "60"
check_env_var "MODEL_TEMPERATURE" "0.1"
check_env_var "TOKENS_PER_MINUTE" "10000"
check_env_var "REQUESTS_PER_MINUTE" "60"
check_env_var "MAX_TOKENS" "4096"

# Proceed with the rest of the script if all checks pass
echo "All required environment variables are set."

# Set default port to 8000 if PORT is not set
PORT="${PORT:-8000}"

uvicorn server_openai:app --host 0.0.0.0 --port $PORT
