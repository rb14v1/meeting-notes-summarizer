from django.test import TestCase, override_settings

from apps.common.ai import is_stub_mode, summarize_meeting_notes


@override_settings(OPENAI_API_KEY="")
class StubModeTests(TestCase):
    def test_is_stub_mode_true_without_api_key(self):
        self.assertTrue(is_stub_mode())

    def test_stub_returns_expected_shape(self):
        result = summarize_meeting_notes("We discussed the roadmap. Alice will follow up with design.")
        self.assertIn("summary", result)
        self.assertIn("action_items", result)
        self.assertIsInstance(result["summary"], str)
        self.assertIsInstance(result["action_items"], list)

    def test_stub_action_item_count_in_range(self):
        result = summarize_meeting_notes("Some notes. More notes. Even more notes here.")
        self.assertGreaterEqual(len(result["action_items"]), 2)
        self.assertLessEqual(len(result["action_items"]), 4)

    def test_stub_is_deterministic_for_same_input(self):
        text = "The team reviewed the budget and agreed on next steps for hiring."
        first = summarize_meeting_notes(text)
        second = summarize_meeting_notes(text)
        self.assertEqual(first, second)

    def test_stub_differs_for_different_input(self):
        first = summarize_meeting_notes("Notes about the sprint planning meeting.")
        second = summarize_meeting_notes("Notes about the budget review meeting.")
        self.assertNotEqual(first["summary"], second["summary"])

    def test_stub_handles_empty_notes(self):
        result = summarize_meeting_notes("")
        self.assertEqual(result["action_items"], [])
        self.assertIn("summary", result)

    def test_stub_summary_is_clearly_labelled(self):
        result = summarize_meeting_notes("Some meeting notes.")
        self.assertIn("STUB", result["summary"])
