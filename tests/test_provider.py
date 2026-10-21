import json
import unittest

from ashlib.provider import ProviderError, request_plan


VALID = {"schema_version": 1, "summary": "Check", "status": "ready", "reason": None,
         "steps": [{"command": "echo okay", "why": "Verify", "risk": "read_only", "expected": "okay"}]}


class Response:
    def __init__(self, body): self.body = body
    def read(self): return self.body.encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.config = {"provider": "openai", "base_url": "https://evil.example/v1", "model": "demo", "api_key": "secret-value"}

    def test_extracts_json_plan(self):
        def opener(req, timeout):
            self.assertEqual(req.full_url, "https://api.openai.com/v1/chat/completions")
            self.assertEqual(req.get_header("Authorization"), "Bearer secret-value")
            self.assertNotIn("temperature", json.loads(req.data.decode("utf-8")))
            self.assertIn("`pkg install NAME` with risk `network`", json.loads(req.data.decode("utf-8"))["messages"][0]["content"])
            return Response(json.dumps({"choices": [{"message": {"content": json.dumps(VALID)}}]}))
        self.assertEqual(request_plan(self.config, "check", opener=opener), VALID)

    def test_rejects_markdown_response(self):
        def opener(req, timeout):
            return Response(json.dumps({"choices": [{"message": {"content": "```json\n{}\n```"}}]}))
        with self.assertRaises(ProviderError):
            request_plan(self.config, "check", opener=opener)

    def test_redacts_key_from_bad_response(self):
        def opener(req, timeout):
            return Response(json.dumps({"choices": [{"message": {"content": "not json secret-value"}}]}))
        with self.assertRaises(ProviderError) as caught:
            request_plan(self.config, "check", opener=opener)
        self.assertNotIn("secret-value", str(caught.exception))
