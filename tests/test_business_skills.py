import unittest

from zexa.agents import AgentOrchestrator, default_agent_registry
from zexa.skills import default_registry


class Reply:
    def __init__(self, text):
        self.text = text


class FakeBrain:
    def __init__(self, answers):
        self.answers = list(answers)

    def chat(self, messages):
        return Reply(self.answers.pop(0))


class BusinessSkillTests(unittest.TestCase):
    def test_business_draft_skills_are_registered_with_no_external_permissions(self):
        registry = default_registry()
        names = {skill.name for skill in registry.list()}
        self.assertTrue({
            "customer_support_drafter",
            "proposal_writer",
            "invoice_drafter",
            "faq_builder",
        }.issubset(names))
        for name in names & {
            "customer_support_drafter", "proposal_writer", "invoice_drafter", "faq_builder"
        }:
            self.assertEqual(registry.get(name).required_permissions, ())

    def test_business_agent_drafts_without_claiming_to_send(self):
        registry = default_registry()
        brain = FakeBrain([
            '{"steps":[{"skill":"proposal_writer","task":"Draft a proposal from supplied scope"}]}',
            "Proposal draft: [scope]. Review before sending.",
        ])
        result = AgentOrchestrator(brain, registry, default_agent_registry()).run(
            "Draft a proposal using the details I provide"
        )
        self.assertEqual(result[0]["agent"], "business")
        self.assertIn("draft", result[0]["result"].lower())


if __name__ == "__main__":
    unittest.main()
