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


if __name__ == "__main__":
    unittest.main()
