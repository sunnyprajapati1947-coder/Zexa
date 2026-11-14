import unittest

from zexa.agents import AgentOrchestrator
from zexa.skills import default_registry


class Reply:
    def __init__(self, text):
        self.text = text


class FakeBrain:
    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []

    def chat(self, messages):
        self.calls.append(messages)
        return Reply(self.answers.pop(0))


class AgentOrchestratorTests(unittest.TestCase):
    def test_routes_steps_to_specialist_agents(self):
        brain = FakeBrain([
            '{"steps":[{"skill":"coding_review","task":"Review this function"}]}',
            "The function needs input validation.",
        ])
        result = AgentOrchestrator(brain, default_registry()).run("Review the code")
        self.assertEqual(result[0]["agent"], "developer")
        self.assertEqual(result[0]["skill"], "coding_review")
        self.assertEqual(len(brain.calls), 2)

    def test_runs_multiple_specialists_in_sequence(self):
        brain = FakeBrain([
            '{"steps":[{"skill":"text_analysis","task":"Extract key claims"},{"skill":"general_assistant","task":"Summarize findings"}]}',
            "Key claim: the project needs tests.",
            "The project should add automated tests.",
        ])
        result = AgentOrchestrator(brain, default_registry()).run("Analyze and summarize")
        self.assertEqual([item["agent"] for item in result], ["analyst", "general"])

    def test_rejects_invalid_goal(self):
        with self.assertRaises(ValueError):
            AgentOrchestrator(FakeBrain([]), default_registry()).run(" ")

    def test_rejects_unrouted_skill(self):
        brain = FakeBrain([
            '{"steps":[{"skill":"unknown_skill","task":"Do something"}]}'
        ])
        with self.assertRaises(KeyError):
            AgentOrchestrator(brain, default_registry()).run("Do something")

    def test_truncates_oversized_agent_output(self):
        brain = FakeBrain([
            '{"steps":[{"skill":"general_assistant","task":"Answer"}]}',
            "x" * 5000,
        ])
        result = AgentOrchestrator(
            brain, default_registry(), max_output_chars=256
        ).run("Answer")
        self.assertTrue(result[0]["result"].endswith("[Output truncated by Zexa budget.]"))


if __name__ == "__main__":
    unittest.main()
