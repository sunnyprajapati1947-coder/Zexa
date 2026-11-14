import unittest

from zexa.planner import create_plan
from zexa.skills import default_registry


class Reply:
    def __init__(self, text):
        self.text = text


class FakeBrain:
    def __init__(self, text):
        self.text = text

    def chat(self, _messages):
        return Reply(self.text)


class PlannerTests(unittest.TestCase):
    def test_accepts_exact_bounded_plan(self):
        brain = FakeBrain('{"steps":[{"skill":"general_assistant","task":"Answer the user"}]}')
        result = create_plan(None, default_registry(), "Help me", brain=brain)
        self.assertEqual(result, [{"skill": "general_assistant", "task": "Answer the user"}])

    def test_rejects_extra_top_level_or_step_fields(self):
        for response in (
            '{"steps":[{"skill":"general_assistant","task":"Answer"}],"execute":"shell"}',
            '{"steps":[{"skill":"general_assistant","task":"Answer","command":"unsafe"}]}',
        ):
            with self.subTest(response=response):
                with self.assertRaises(RuntimeError):
                    create_plan(None, default_registry(), "Help", brain=FakeBrain(response))

    def test_rejects_unknown_skill_and_oversized_goal(self):
        with self.assertRaisesRegex(RuntimeError, "not registered"):
            create_plan(
                None, default_registry(), "Help",
                brain=FakeBrain('{"steps":[{"skill":"unknown","task":"Do it"}]}'),
            )
        with self.assertRaises(ValueError):
            create_plan(None, default_registry(), "x" * 4001, brain=FakeBrain("{}"))

    def test_rejects_non_text_goal(self):
        with self.assertRaisesRegex(ValueError, "text"):
            create_plan(None, default_registry(), None, brain=FakeBrain("{}"))


if __name__ == "__main__":
    unittest.main()
