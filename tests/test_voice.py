import unittest

from zexa.android import TermuxVoice


class TermuxVoiceTests(unittest.TestCase):
    def test_listen_returns_transcript(self):
        calls = []

        class Result:
            stdout = "  hello Zexa  "

        def fake_run(command, **kwargs):
            calls.append((command, kwargs))
            return Result()

        voice = TermuxVoice(which=lambda name: "/fake/" + name, run=fake_run)
        self.assertEqual(voice.listen(), "hello Zexa")
        self.assertEqual(calls[0][0], ["/fake/termux-speech-to-text"])
        self.assertEqual(calls[0][1]["timeout"], 60)

    def test_listen_rejects_missing_capability(self):
        voice = TermuxVoice(which=lambda name: None, run=lambda *a, **k: None)
        with self.assertRaises(RuntimeError):
            voice.listen()

    def test_speak_uses_argument_list_and_rejects_empty_text(self):
        calls = []

        def fake_run(command, **kwargs):
            calls.append((command, kwargs))

        voice = TermuxVoice(which=lambda name: "/fake/" + name, run=fake_run)
        voice.speak("Hello Zexa")
        self.assertEqual(calls[0][0], ["/fake/termux-tts-speak", "Hello Zexa"])
        with self.assertRaises(ValueError):
            voice.speak("   ")

    def test_speak_rejects_missing_capability(self):
        voice = TermuxVoice(which=lambda name: None, run=lambda *a, **k: None)
        with self.assertRaises(RuntimeError):
            voice.speak("Hello")


if __name__ == "__main__":
    unittest.main()
