import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from zexa import cli


class FakeReply:
    def __init__(self, text):
        self.text = text


class FakeBrain:
    def __init__(self, events, answer="Namaste! Main Zexa hoon."):
        self.events = events
        self.answer = answer

    def chat(self, messages):
        self.events.append(("chat", messages))
        return FakeReply(self.answer)


class CliVoiceTests(unittest.TestCase):
    def test_voice_uses_selected_brain_and_speaks_reply(self):
        events = []

        class FakeVoice:
            def listen(self):
                events.append("listen")
                return "hello Zexa"

            def speak(self, text):
                events.append(("speak", text))

        output = io.StringIO()
        with patch.object(sys, "argv", ["zexa", "voice"]), \
             patch.object(cli, "load_env_file"), \
             patch.dict(os.environ, {"GROQ_API_KEY": "", "ZEXA_BRAIN_MODE": "auto"}), \
             patch.object(cli, "build_brain_router", return_value=FakeBrain(events)), \
             patch.object(cli, "TermuxVoice", FakeVoice), \
             redirect_stdout(output):
            cli.main()

        self.assertEqual(events[0], "listen")
        self.assertEqual(events[1][0], "chat")
        self.assertEqual(events[1][1][-1], {"role": "user", "content": "hello Zexa"})
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

        def fake_route(config, history, transcript, brain=None):
            events.append(("route", [dict(item) for item in history], transcript))
            return {"intent": "question", "reply": "Namaste, main sun raha hoon."}

        output = io.StringIO()
        with patch.object(sys, "argv", ["zexa", "converse"]), \
             patch.object(cli, "load_env_file"), \
             patch.dict(os.environ, {"GROQ_API_KEY": "", "ZEXA_BRAIN_MODE": "auto"}), \
             patch.object(cli, "build_brain_router", return_value=FakeBrain(events)), \
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
        captures = iter([
            "hello",
            RuntimeError("No speech transcript was returned."),
            RuntimeError("No speech transcript was returned."),
            "I am back",
            "stop",
        ])

        class FakeVoice:
            def listen(self):
                value = next(captures)
                if isinstance(value, Exception):
                    raise value
                return value

            def speak(self, text):
                events.append(text)

        def fake_route(config, history, transcript, brain=None):
            return {"intent": "question", "reply": "I am listening."}

        output = io.StringIO()
        with patch.object(sys, "argv", ["zexa", "converse"]), \
             patch.object(cli, "load_env_file"), \
             patch.dict(os.environ, {"GROQ_API_KEY": "", "ZEXA_BRAIN_MODE": "auto"}), \
             patch.object(cli, "build_brain_router", return_value=FakeBrain(events)), \
             patch.object(cli, "TermuxVoice", FakeVoice), \
             patch.object(cli, "route_utterance", side_effect=fake_route), \
             patch.object(cli.time, "sleep"), \
             redirect_stdout(output):
            cli.main()

        self.assertEqual(events, ["I am listening.", "I am listening."])
        self.assertIn("You: I am back", output.getvalue())
        self.assertIn("Voice conversation ended.", output.getvalue())
        self.assertNotIn("paused after 3 empty captures", output.getvalue())

    def test_explicit_flashlight_commands_are_recognized(self):
        self.assertEqual(cli._explicit_torch_request("flash on karo"), "on")
        self.assertEqual(cli._explicit_torch_request("torch band karo"), "off")
        self.assertEqual(cli._explicit_torch_request("फ्लैश चालू करो"), "on")
        self.assertEqual(cli._explicit_torch_request("फ्लैश बंद करो"), "off")
        self.assertIsNone(cli._explicit_torch_request("flash kaise kaam karta hai"))
        self.assertIsNone(cli._explicit_torch_request("phone on karo"))


if __name__ == "__main__":
    unittest.main()
