import io
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from zexa import cli


class CliVoiceTests(unittest.TestCase):
    def test_voice_sends_one_transcript_to_groq_and_speaks_reply(self):
        events = []

        class FakeVoice:
            def listen(self):
                events.append("listen")
                return "hello Zexa"

            def speak(self, text):
                events.append(("speak", text))

        def fake_chat(config, messages):
            events.append(("chat", config, messages))
            return "Namaste! Main Zexa hoon."

        output = io.StringIO()
        with patch.object(sys, "argv", ["zexa", "voice"]), \
             patch.object(cli, "load_env_file"), \
             patch.object(cli, "get_config", return_value={"model": "test-model"}), \
             patch.object(cli, "TermuxVoice", FakeVoice), \
             patch.object(cli, "chat", side_effect=fake_chat), \
             redirect_stdout(output):
            cli.main()

        self.assertEqual(events[0], "listen")
        self.assertEqual(events[1][0], "chat")
        self.assertEqual(events[1][2][-1], {"role": "user", "content": "hello Zexa"})
        self.assertEqual(events[2], ("speak", "Namaste! Main Zexa hoon."))
        self.assertIn("You: hello Zexa", output.getvalue())
        self.assertIn("Zexa: Namaste! Main Zexa hoon.", output.getvalue())


    def test_converse_keeps_context_and_stops_on_spoken_exit(self):
        events = []
        transcripts = iter(["hello Zexa", "what did I just say?", "stop"])

        class FakeVoice:
            def listen(self):
                value = next(transcripts)
                events.append(("listen", value))
                return value

            def speak(self, text):
                events.append(("speak", text))

        def fake_route(config, history, transcript):
            events.append(("route", [dict(item) for item in history], transcript))
            return {"intent": "question", "reply": "Namaste, main sun raha hoon."}

        output = io.StringIO()
        with patch.object(sys, "argv", ["zexa", "converse"]), \
             patch.object(cli, "load_env_file"), \
             patch.object(cli, "get_config", return_value={"model": "test-model"}), \
             patch.object(cli, "TermuxVoice", FakeVoice), \
             patch.object(cli, "route_utterance", side_effect=fake_route), \
             redirect_stdout(output):
            cli.main()

        routes = [event for event in events if event[0] == "route"]
        self.assertEqual(len(routes), 2)
        self.assertEqual(routes[0][2], "hello Zexa")
        self.assertEqual(routes[1][1][-2:], [
            {"role": "user", "content": "hello Zexa"},
            {"role": "assistant", "content": "Namaste, main sun raha hoon."},
        ])
        self.assertEqual(len([event for event in events if event[0] == "speak"]), 2)
        self.assertIn("Voice conversation ended.", output.getvalue())


    def test_converse_recovers_after_empty_captures(self):
        events = []
        captures = iter(["hello", RuntimeError("No speech transcript was returned."), RuntimeError("No speech transcript was returned."), "I am back", "stop"])

        class FakeVoice:
            def listen(self):
                value = next(captures)
                if isinstance(value, Exception):
                    raise value
                return value

            def speak(self, text):
                events.append(text)

        def fake_route(config, history, transcript):
            return {"intent": "question", "reply": "I am listening."}

        output = io.StringIO()
        with patch.object(sys, "argv", ["zexa", "converse"]), \
             patch.object(cli, "load_env_file"), \
             patch.object(cli, "get_config", return_value={"model": "test-model"}), \
             patch.object(cli, "TermuxVoice", FakeVoice), \
             patch.object(cli, "route_utterance", side_effect=fake_route), \
             patch.object(cli.time, "sleep"), \
             redirect_stdout(output):
            cli.main()

        self.assertEqual(events, ["I am listening.", "I am listening."])
        self.assertIn("You: I am back", output.getvalue())
        self.assertIn("Voice conversation ended.", output.getvalue())
        self.assertNotIn("paused after 3 empty captures", output.getvalue())


if __name__ == "__main__":
    unittest.main()
