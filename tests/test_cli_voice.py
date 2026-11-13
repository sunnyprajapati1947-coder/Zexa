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

        def fake_chat(config, messages):
            events.append(("chat", [dict(item) for item in messages]))
            return "Namaste, main sun raha hoon."

        output = io.StringIO()
        with patch.object(sys, "argv", ["zexa", "converse"]), \
             patch.object(cli, "load_env_file"), \
             patch.object(cli, "get_config", return_value={"model": "test-model"}), \
             patch.object(cli, "TermuxVoice", FakeVoice), \
             patch.object(cli, "chat", side_effect=fake_chat), \
             redirect_stdout(output):
            cli.main()

        chats = [event for event in events if event[0] == "chat"]
        self.assertEqual(len(chats), 2)
        self.assertEqual(chats[0][1][-1], {"role": "user", "content": "hello Zexa"})
        self.assertEqual(chats[1][1][-2:], [
            {"role": "user", "content": "hello Zexa"},
            {"role": "assistant", "content": "Namaste, main sun raha hoon."},
        ])
        self.assertEqual(len([event for event in events if event[0] == "speak"]), 2)
        self.assertIn("Voice conversation ended.", output.getvalue())


if __name__ == "__main__":
    unittest.main()
