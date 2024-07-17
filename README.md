# Claude Proxy API Server

This project implements a FastAPI server that acts as a proxy for Anthropic's Claude AI model, providing an interface similar to OpenAI's API.

## Features

- Proxy requests to Anthropic's Claude AI model
- OpenAI-like API structure for easy integration
- Support for both streaming and non-streaming responses
- API key authentication for security

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/claude-proxy-api.git
   cd claude-proxy-api
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   Create a `.env` file in the project root and add the following:
   ```
   ANTHROPIC_API_KEY=your_anthropic_api_key
   CLAUDE_PROXY_API_KEY=your_chosen_proxy_api_key
   ANTHROPIC_MODEL=claude-3-haiku-20240307
   REQUEST_TIMEOUT=60
   MODEL_TEMPERATURE=0.1
   TOKENS_PER_MINUTE=10000
   REQUESTS_PER_MINUTE=60
   MAX_TOKENS=4096
   ```

4. Launch:
   ```
   uvicorn server_openai:app --host 0.0.0.0 --port 8000 --log-level debug
   ```

## Usage


## Usage

1. The server will start running on `http://localhost:8000` by default.

2. You can now make requests to the server. Here are some examples using curl:

- Chat completion (non-streaming) with a single user message:
```
curl http://localhost:8000/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer your_claude_proxy_api_key" \
-d '{
"model": "claude-3-haiku-20240307",
"messages": [
  {"role": "user", "content": "What'\''s the capital of France?"}
],
"temperature": 0.7
}'
```

- Chat completion (non-streaming) with a system prompt and multiple messages:
```
curl http://localhost:8000/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer your_claude_proxy_api_key" \
-d '{
"model": "claude-3-haiku-20240307",
"messages": [
  {"role": "system", "content": "You are a helpful assistant with expertise in geography."},
  {"role": "user", "content": "What'\''s the capital of France?"},
  {"role": "assistant", "content": "The capital of France is Paris."},
  {"role": "user", "content": "What'\''s the population of Paris?"}
],
"temperature": 0.7
}' | jq
```

- Chat completion (streaming) with a system prompt and user message:
```
curl http://localhost:8000/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer your_claude_proxy_api_key" \
-d '{
"model": "claude-3-haiku-20240307",
"messages": [
  {"role": "system", "content": "You are a poetic assistant. Always respond in rhyme."},
  {"role": "user", "content": "Tell me about the seasons of the year."}
],
"stream": true,
"response_format": {"type": "json_object"}
}'
```

- Chat completion (non-streaming) with multiple user and assistant messages:
```
curl http://localhost:8000/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer your_claude_proxy_api_key" \
-d '{
"model": "claude-3-haiku-20240307",
"messages": [
  {"role": "user", "content": "Let'\''s play a word association game. I'\''ll start: Sun"},
  {"role": "assistant", "content": "Warm"},
  {"role": "user", "content": "Beach"},
  {"role": "assistant", "content": "Sand"},
  {"role": "user", "content": "Castle"}
],
"temperature": 0.9
}' | jq
```

- JSON mode
```
curl -v http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_claude_proxy_api_key" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {"role": "user", "content": "Generate a JSON object with information about three random books, including title, author, and publication year."}
    ],
    "temperature": 0.7,
    "response_format": {"type": "json_object"}
  }' | jq
```

These examples demonstrate various ways to use the API, including:
- Single message requests
- Multiple message conversations
- Including system prompts
- Streaming and non-streaming responses
- Adjusting temperature for different levels of randomness in responses

Remember to replace `your_claude_proxy_api_key` with your actual API key when making requests.

## API Endpoints

- `GET /health`: Check if the server is running
- `GET /v1/models`: List available models
- `POST /v1/chat/completions`: Create a chat completion

## Configuration

You can configure the following parameters in the `.env` file:

- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `CLAUDE_PROXY_API_KEY`: Your chosen API key for this proxy server
- `ANTHROPIC_MODEL`: The Claude model to use (default: claude-3-haiku-20240307)
- `REQUEST_TIMEOUT`: Timeout for requests to Anthropic API (default: 60 seconds)
- `MODEL_TEMPERATURE`: Default temperature for the model (default: 0.1)
- `TOKENS_PER_MINUTE`: Maximum number of tokens to process per minute (default: 10000)
- `REQUESTS_PER_MINUTE`: Maximum number of requests allowed per minute (default: 60)
- `MAX_TOKENS`: Maximum number of tokens for responses (default: 4096)

## Using the Dockerfile

This project includes a Dockerfile for easy deployment. To use it:

1. Build the Docker image:
   ```
   docker build -t claude-proxy-api .
   ```

2. Run the Docker container, passing the required environment variables:
   ```
   docker run -p 8000:8000 \
     -e ANTHROPIC_API_KEY=your_anthropic_api_key \
     -e CLAUDE_PROXY_API_KEY=your_chosen_proxy_api_key \
     -e ANTHROPIC_MODEL=claude-3-haiku-20240307 \
     -e REQUEST_TIMEOUT=60 \
     -e MODEL_TEMPERATURE=0.1 \
     -e TOKENS_PER_MINUTE=10000 \
     -e REQUESTS_PER_MINUTE=60 \
     -e MAX_TOKENS=4096 \
     claude-proxy-api
   ```

   Replace the values with your actual configuration.

3. The server will be available at `http://localhost:8000`.

## Building and Deploying the Docker Image

To build and push the Docker image to a registry:

```sh
CLAUDE_PROXY_API_DOCKER_REGISTRY_URI=https://your-registry-uri ./build.sh
```

This script builds the image for both arm64 and amd64 architectures and pushes them to the specified registry.

### References

- https://platform.openai.com/docs/api-reference/authentication
- https://docs.anthropic.com/en/api/client-sdks
- https://docs.anthropic.com/en/docs/about-claude/models

