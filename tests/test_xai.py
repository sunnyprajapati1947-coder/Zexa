import json
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from zexa.xai import chat


class XaiClientTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "api_key": "test-only-not-a-real-key",
            "model": "grok-4.7",
            "base_url": "https://api.x.ai/v1",
            "reasoning_effort": "low",
            "timeout": "30",
        }

    @patch("zexa.xai.urlopen")
    def test_uses_responses_endpoint_and_extracts_visible_text(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "output": [
                {"type": "reasoning", "encrypted_content": "opaque"},
                {"type": "message", "role": "assistant", "content": [
                    {"type": "output_text", "text": "Hello from Grok"}
                ]},
            ]
        }).encode()
        urlopen.return_value = response

        answer = chat(self.config, [{"role": "user", "content": "Hello"}])

        self.assertEqual(answer, "Hello from Grok")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.x.ai/v1/responses")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-only-not-a-real-key")
        payload = json.loads(request.data.decode())
        self.assertEqual(payload["model"], "grok-4.7")
        self.assertFalse(payload["store"])
        self.assertEqual(payload["reasoning"]["effort"], "low")

    @patch("zexa.xai.urlopen", side_effect=URLError("offline"))
    def test_network_error_is_classified_for_router_fallback(self, _urlopen):
        with self.assertRaisesRegex(RuntimeError, "Could not reach xAI API"):
            chat(self.config, [{"role": "user", "content": "Hello"}])

    @patch("zexa.xai.urlopen")
    def test_http_auth_error_is_not_misclassified_as_network(self, urlopen):
        from urllib.error import HTTPError
        import io
        urlopen.side_effect = HTTPError(
            "https://api.x.ai/v1/responses", 401, "Unauthorized", {},
            io.BytesIO(b"invalid key"),
        )
        with self.assertRaisesRegex(RuntimeError, "HTTP 401"):
            chat(self.config, [{"role": "user", "content": "Hello"}])

    def test_rejects_response_without_visible_text(self):
        from zexa.xai import _extract_text
        with self.assertRaisesRegex(RuntimeError, "no visible assistant text"):
            _extract_text({"output": [{"type": "reasoning"}]})


if __name__ == "__main__":
    unittest.main()
