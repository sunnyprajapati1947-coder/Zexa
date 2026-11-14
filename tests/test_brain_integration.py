import unittest

from zexa.intent import route_utterance
from zexa.planner import create_plan
from zexa.skills import default_registry


class FakeReply:
    def __init__(self, text):
        self.text = text


class FakeBrain:
    def __init__(self, text):
        self.text = text
        self.calls = []

    def chat(self, messages):
        self.calls.append(messages)
        return FakeReply(self.text)


class RoutedBrainIntegrationTests(unittest.TestCase):
    def test_voice_intent_uses_selected_brain(self):
        brain = FakeBrain('{"intent":"question","reply":"Namaste"}')
        result = route_utterance(None, [], "Namaste", brain=brain)
        self.assertEqual(result, {"intent": "question", "reply": "Namaste"})
        self.assertEqual(len(brain.calls), 1)

    def test_planner_uses_selected_brain_and_validates_skill(self):
        brain = FakeBrain(
            '{"steps":[{"skill":"general_assistant","task":"Explain the requested topic"}]}'
        )
        result = create_plan(None, default_registry(), "Explain AI", brain=brain)
        self.assertEqual(result, [
            {"skill": "general_assistant", "task": "Explain the requested topic"}
        ])
        self.assertEqual(len(brain.calls), 1)

    def test_planner_rejects_unregistered_skill_from_brain(self):
        brain = FakeBrain('{"steps":[{"skill":"run_shell","task":"Run command"}]}')
        with self.assertRaisesRegex(RuntimeError, "not registered"):
            create_plan(None, default_registry(), "Do something", brain=brain)


if __name__ == "__main__":
    unittest.main()
