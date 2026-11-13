import unittest
from unittest.mock import patch

from zexa.intent import route_utterance


class IntentRoutingTests(unittest.TestCase):
    @patch("zexa.intent.chat", return_value='{"intent":"question","reply":"Main jawab de sakta hoon."}')
    def test_question_is_routed_as_question(self, mocked_chat):
        result = route_utterance({"model": "test"}, [], "Tum kya kar sakte ho?")
        self.assertEqual(result, {"intent": "question", "reply": "Main jawab de sakta hoon."})
        mocked_chat.assert_called_once()

    @patch("zexa.intent.chat", return_value='{"intent":"task_request","reply":"Request samajh gaya. Koi action execute nahi hua."}')
    def test_task_request_is_only_acknowledged_not_executed(self, mocked_chat):
        result = route_utterance({"model": "test"}, [], "Mere liye website banao")
        self.assertEqual(result["intent"], "task_request")
        self.assertIn("execute nahi hua", result["reply"])

    @patch("zexa.intent.chat", return_value='{"intent":"noise","reply":""}')
    def test_noise_is_skipped(self, mocked_chat):
        self.assertEqual(route_utterance({"model": "test"}, [], "   "), {"intent": "noise", "reply": ""})
        mocked_chat.assert_not_called()

    @patch("zexa.intent.chat", return_value="A normal useful reply")
    def test_non_json_response_fails_safe_as_conversation(self, mocked_chat):
        result = route_utterance({"model": "test"}, [], "Hello")
        self.assertEqual(result, {"intent": "conversation", "reply": "A normal useful reply"})


if __name__ == "__main__":
    unittest.main()
