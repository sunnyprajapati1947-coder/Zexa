import unittest

from zexa.skills import Skill, SkillRegistry, default_registry


class SkillContractTests(unittest.TestCase):
    def test_default_skills_declare_schemas_and_budgets(self):
        for skill in default_registry().list():
            self.assertTrue(skill.input_schema)
            self.assertTrue(skill.output_schema)
            self.assertGreaterEqual(skill.timeout_seconds, 1)
            self.assertIn(skill.risk_level, {"low", "medium", "high", "critical"})

    def test_disabled_skill_is_hidden_from_planners_and_cannot_be_loaded(self):
        registry = default_registry()
        self.assertTrue(registry.set_enabled("coding_review", False))
        self.assertNotIn("coding_review", {skill.name for skill in registry.list()})
        with self.assertRaisesRegex(KeyError, "disabled"):
            registry.get("coding_review")
        self.assertEqual(len(registry.all()), 3)

    def test_invalid_risk_and_unbounded_timeout_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "risk_level"):
            Skill("unsafe", "Description", "Instruction", risk_level="unknown")
        with self.assertRaisesRegex(ValueError, "timeout"):
            Skill("slow", "Description", "Instruction", timeout_seconds=9999)

    def test_registry_rejects_duplicate_skill(self):
        registry = SkillRegistry()
        skill = Skill("sample", "Description", "Instruction")
        registry.register(skill)
        with self.assertRaisesRegex(ValueError, "already registered"):
            registry.register(skill)


if __name__ == "__main__":
    unittest.main()
