import argparse
import json
import logging
import os
import time
import uuid
from typing import AsyncGenerator, Dict

from datetime import datetime
from http import HTTPStatus
import uvicorn
from dotenv import load_dotenv
from fastapi import Request, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from anthropic import AsyncAnthropic

# Load environment variables
load_dotenv()


# Logger setup
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def setup_logger(logger_name: str) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    json_formatter = JSONFormatter()
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)
    return logger


logger = setup_logger("server-openai")

# FastAPI app initialization
app = FastAPI()

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Environment variables
CLAUDE_PROXY_API_KEY = os.getenv("CLAUDE_PROXY_API_KEY")
if not CLAUDE_PROXY_API_KEY:
    raise ValueError("CLAUDE_PROXY_API_KEY must be set")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY must be set")

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", 60))
MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", 0.7))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", 4096))

# Anthropic client initialization
client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


async def verify_api_key(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    api_key = authorization.split("Bearer ")[1]
    if api_key != CLAUDE_PROXY_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


# Error response helper
def create_error_response(status_code: HTTPStatus, message: str) -> JSONResponse:
    return JSONResponse(
        {"error": {"message": message, "type": "invalid_request_error"}},
        status_code=status_code.value,
    )


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc):
    return create_error_response(HTTPStatus.BAD_REQUEST, str(exc))


# API endpoints
@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(content={"status": "ok"}, status_code=HTTPStatus.OK.value)


@app.get("/v1/models")
async def show_available_models(authorization: str = Header(...)):
    await verify_api_key(authorization)
    model_card = {
        "id": ANTHROPIC_MODEL,
        "object": "model",
        "created": int(time.time()),
        "owned_by": "anthropic",
    }
    return {"data": [model_card], "object": "list"}


@app.post("/v1/chat/completions")
async def create_chat_completion(request: Request, authorization: str = Header(...)):
    await verify_api_key(authorization)

    logger.info("Endpoint hit: /v1/chat/completions")
    try:
        body = await request.body()
        logger.debug(f"Raw request body: {body.decode()}")

        data = await request.json()
        logger.info("JSON parsed successfully")
        logger.debug(f"Request data: {data}")

        messages = data.get("messages", [])
        logger.debug(f"Number of messages: {len(messages)}")

        max_tokens = data.get("max_tokens", MAX_TOKENS)
        temperature = data.get("temperature")
        stream = data.get("stream", False)
        response_format = data.get("response_format")

        logger.info(
            f"Processing request: stream={stream}, max_tokens={max_tokens}, temperature={temperature}, response_format={response_format}"
        )
        logger.debug(f"Messages: {messages}")

        # Extract system message if present
        system_message = None
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                user_messages.append(msg)

        # Prepare API call parameters
        api_params = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": max_tokens,
            "messages": user_messages,
        }
        if system_message:
            api_params["system"] = system_message
        if temperature is not None:
            api_params["temperature"] = temperature

        # Handle response_format
        json_response_required = (
            response_format and response_format.get("type") == "json_object"
        )
        if json_response_required:
            json_instruction = (
                "You must respond with a valid JSON object only, without any additional text. "
                "Do not include markdown formatting or code blocks. "
                "The response should be parseable by a JSON parser."
            )

            if system_message:
                api_params["system"] = f"{system_message}\n\n{json_instruction}"
            else:
                api_params["system"] = json_instruction

        try:
            if stream:
                logger.info("Starting streaming response")
                return StreamingResponse(
                    chat_completion_stream(api_params, json_response_required),
                    media_type="text/event-stream",
                )
            else:
                logger.info("Starting non-streaming response")
                response = await client.messages.create(**api_params)
                logger.debug(f"Received response from Anthropic: {response}")

                if json_response_required:
                    # Attempt to parse and format the response as JSON
                    try:
                        content = response.content[0].text if response.content else ""
                        json_content = json.loads(content)
                        formatted_json = json.dumps(
                            json_content, ensure_ascii=False, indent=2
                        )
                        response.content[0].text = formatted_json
                    except json.JSONDecodeError:
                        logger.error("Failed to parse response as JSON")
                        return create_error_response(
                            HTTPStatus.INTERNAL_SERVER_ERROR,
                            "Failed to generate a valid JSON response",
                        )

                return JSONResponse(create_chat_completion_response(response))
        except Exception as e:
            logger.error(f"Error in request to Anthropic API: {str(e)}", exc_info=True)
            return create_error_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                f"Error in request to Anthropic API: {str(e)}",
            )
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return create_error_response(HTTPStatus.BAD_REQUEST, f"Invalid JSON: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error in create_chat_completion: {str(e)}")
        return create_error_response(
            HTTPStatus.INTERNAL_SERVER_ERROR, f"Internal server error: {str(e)}"
        )


async def chat_completion_stream(
    api_params: Dict, json_response_required: bool
) -> AsyncGenerator[str, None]:
    try:
        completion_id = f"chatcmpl-{uuid.uuid4()}"
        created_time = int(time.time())

        async with client.messages.stream(**api_params) as stream:
            yield format_stream_response(completion_id, created_time, "start")

            buffer = ""
            async for event in stream:
                if event.type == "content_block_delta":
                    buffer += event.delta.text
                    if json_response_required:
                        # For JSON responses, stream complete objects or array elements
                        chunks = split_json_chunks(buffer)
                        for chunk in chunks[:-1]:  # All complete chunks
                            yield format_stream_response(
                                completion_id, created_time, "delta", chunk
                            )
                        buffer = chunks[-1]  # Keep the incomplete chunk in the buffer
                    else:
                        # For non-JSON responses, stream by sentences or fixed chunk size
                        chunks = split_text_chunks(buffer)
                        for chunk in chunks[:-1]:  # All complete chunks
                            yield format_stream_response(
                                completion_id, created_time, "delta", chunk
                            )
                        buffer = chunks[-1]  # Keep the incomplete chunk in the buffer

            # Stream any remaining content in the buffer
            if buffer:
                yield format_stream_response(
                    completion_id, created_time, "delta", buffer
                )

            yield format_stream_response(completion_id, created_time, "stop")

        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.exception(f"Error in streaming response: {str(e)}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"


def split_json_chunks(text):
    chunks = []
    depth = 0
    current_chunk = ""

    for char in text:
        current_chunk += char
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                chunks.append(current_chunk)
                current_chunk = ""

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def split_text_chunks(text, max_chunk_size=100):
    chunks = []
    current_chunk = ""

    for sentence in text.split(". "):
        if len(current_chunk) + len(sentence) > max_chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += ". " + sentence if current_chunk else sentence

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def format_stream_response(
    completion_id: str, created_time: int, event_type: str, content: str = ""
):
    response = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created_time,
        "model": ANTHROPIC_MODEL,
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": None,
            }
        ],
    }

    if event_type == "start":
        response["choices"][0]["delta"] = {"role": "assistant"}
    elif event_type == "delta":
        response["choices"][0]["delta"] = {"content": content}
    elif event_type == "stop":
        response["choices"][0]["finish_reason"] = "stop"

    return f"data: {json.dumps(response)}\n\n"


def create_chat_completion_response(response):
    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": ANTHROPIC_MODEL,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response.content[0].text if response.content else "",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Claude Proxy API server.")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="host name")
    parser.add_argument("--port", type=str, default="8000", help="port number")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=int(args.port), log_level="debug")
