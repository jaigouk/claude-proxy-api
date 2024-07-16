import json
import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from server_openai import app, CLAUDE_PROXY_API_KEY
from anthropic import APIError, APIResponseValidationError

class TestServerOpenAI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.headers = {"Authorization": f"Bearer {CLAUDE_PROXY_API_KEY}"}

class TestHealthEndpoint(TestServerOpenAI):
    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

class TestModelsEndpoint(TestServerOpenAI):
    def test_show_available_models(self):
        response = self.client.get("/v1/models", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("data", data)
        self.assertEqual(len(data["data"]), 1)
        self.assertEqual(data["data"][0]["object"], "model")

    def test_show_available_models_unauthorized(self):
        response = self.client.get("/v1/models")
        self.assertEqual(response.status_code, 400)

class TestChatCompletionsEndpoint(TestServerOpenAI):
    @patch("server_openai.client.messages.create")
    async def test_create_chat_completion(self, mock_create):
        mock_response = AsyncMock()
        mock_response.content = [AsyncMock(text="Test response")]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20
        mock_create.return_value = mock_response

        payload = {
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 100,
            "temperature": 0.7,
        }
        response = self.client.post("/v1/chat/completions", headers=self.headers, json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["choices"][0]["message"]["content"], "Test response")
        self.assertEqual(data["usage"]["total_tokens"], 30)

    def test_create_chat_completion_no_messages(self):
        payload = {"max_tokens": 100}
        response = self.client.post("/v1/chat/completions", headers=self.headers, json=payload)
        self.assertEqual(response.status_code, 400)

    def test_create_chat_completion_invalid_json(self):
        response = self.client.post("/v1/chat/completions", headers=self.headers, content="invalid json")
        self.assertEqual(response.status_code, 400)

    @patch("server_openai.client.messages.create")
    async def test_create_chat_completion_json_response(self, mock_create):
        mock_response = AsyncMock()
        mock_response.content = [AsyncMock(text='{"key": "value"}')]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20
        mock_create.return_value = mock_response

        payload = {
            "messages": [{"role": "user", "content": "Return JSON"}],
            "response_format": {"type": "json_object"}
        }
        response = self.client.post("/v1/chat/completions", headers=self.headers, json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(json.loads(data["choices"][0]["message"]["content"]), {"key": "value"})

    @patch("server_openai.client.messages.create")
    async def test_create_chat_completion_with_system_message(self, mock_create):
        mock_response = AsyncMock()
        mock_response.content = [AsyncMock(text="System-influenced response")]
        mock_response.usage.input_tokens = 15
        mock_response.usage.output_tokens = 25
        mock_create.return_value = mock_response

        payload = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Hello"}
            ],
        }
        response = self.client.post("/v1/chat/completions", headers=self.headers, json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["choices"][0]["message"]["content"], "System-influenced response")

class TestStreamingResponses(TestServerOpenAI):
    @patch("server_openai.client.messages.stream")
    async def test_streaming_response(self, mock_stream):
        mock_stream_response = AsyncMock()
        mock_stream_response.__aiter__.return_value = [
            AsyncMock(type="content_block_delta", delta=AsyncMock(text="Hello")),
            AsyncMock(type="content_block_delta", delta=AsyncMock(text=" world")),
        ]
        mock_stream.return_value.__aenter__.return_value = mock_stream_response

        payload = {
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": True
        }
        response = self.client.post("/v1/chat/completions", headers=self.headers, json=payload)

        self.assertEqual(response.status_code, 200)
        content = b"".join(response.iter_bytes())
        self.assertIn(b"Hello", content)
        self.assertIn(b"world", content)

    @patch("server_openai.client.messages.stream")
    async def test_streaming_json_response(self, mock_stream):
        mock_stream_response = AsyncMock()
        mock_stream_response.__aiter__.return_value = [
            AsyncMock(type="content_block_delta", delta=AsyncMock(text='{"part1": "value1"')),
            AsyncMock(type="content_block_delta", delta=AsyncMock(text=', "part2": "value2"}')),
        ]
        mock_stream.return_value.__aenter__.return_value = mock_stream_response

        payload = {
            "messages": [{"role": "user", "content": "Return JSON"}],
            "stream": True,
            "response_format": {"type": "json_object"}
        }
        response = self.client.post("/v1/chat/completions", headers=self.headers, json=payload)

        self.assertEqual(response.status_code, 200)
        content = b"".join(response.iter_bytes())
        self.assertIn(b'"part1": "value1"', content)
        self.assertIn(b'"part2": "value2"', content)

class TestErrorHandling(TestServerOpenAI):
    def test_invalid_api_key(self):
        headers = {"Authorization": "Bearer invalid_key"}
        response = self.client.post("/v1/chat/completions", headers=headers, json={})
        self.assertEqual(response.status_code, 401)

    @patch("server_openai.client.messages.create")
    async def test_anthropic_api_error(self, mock_create):
        mock_create.side_effect = APIError(request=AsyncMock(), message="Anthropic API Error")

        payload = {"messages": [{"role": "user", "content": "Hello"}]}
        response = self.client.post("/v1/chat/completions", headers=self.headers, json=payload)

        self.assertEqual(response.status_code, 500)
        self.assertIn("Anthropic API error", response.json()["error"]["message"])

    @patch("server_openai.client.messages.create")
    async def test_unexpected_error(self, mock_create):
        mock_create.side_effect = Exception("Unexpected error")

        payload = {"messages": [{"role": "user", "content": "Hello"}]}
        response = self.client.post("/v1/chat/completions", headers=self.headers, json=payload)

        self.assertEqual(response.status_code, 500)
        self.assertIn("Unexpected error", response.json()["error"]["message"])

if __name__ == "__main__":
    unittest.main()
