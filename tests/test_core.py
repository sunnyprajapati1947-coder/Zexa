import unittest

from zexa.skills import default_registry
from zexa.tools import default_router


class CoreTests(unittest.TestCase):
    def test_default_skills_are_registered(self):
        names = {skill.name for skill in default_registry().list()}
        self.assertTrue({"general_assistant", "text_analysis", "coding_review", "customer_support_drafter", "proposal_writer", "invoice_drafter", "faq_builder"}.issubset(names))

    def test_calculator(self):
        router = default_router()
        self.assertEqual(router.run("calculator", "(12 + 8) * 2"), "40")

    def test_tool_router_rejects_unknown_tool(self):
        with self.assertRaises(KeyError):
            default_router().run("shell", "echo unsafe")

    def test_calculator_rejects_code(self):
        with self.assertRaises(ValueError):
            default_router().run("calculator", "__import__('os').system('id')")


if __name__ == "__main__":
    unittest.main()
