from django.test import TestCase

from apps.accounts.models import User
from apps.meetings.models import ActionItem, Meeting, MeetingSummary


class SeedDataMigrationTests(TestCase):
    """Verifies the 0002_seed_demo_data data migration (run automatically
    when the test database is created) produced the documented demo
    dataset."""

    @classmethod
    def setUpTestData(cls):
        cls.member = User.objects.get(email="member@example.com")
        cls.admin = User.objects.get(email="admin@example.com")

    def test_demo_users_exist_with_expected_roles_and_password(self):
        self.assertTrue(self.member.check_password("demo12345"))
        self.assertEqual(self.member.role, User.Role.MEMBER)
        self.assertTrue(self.admin.check_password("demo12345"))
        self.assertEqual(self.admin.role, User.Role.ADMIN)

    def test_user_count(self):
        self.assertEqual(User.objects.count(), 2)

    def test_meeting_count_in_expected_range(self):
        count = Meeting.objects.count()
        self.assertGreaterEqual(count, 8)
        self.assertLessEqual(count, 10)

    def test_most_meetings_have_a_summary(self):
        total = Meeting.objects.count()
        summarized = MeetingSummary.objects.count()
        self.assertGreater(summarized, 0)
        self.assertGreaterEqual(summarized, total - 2)

    def test_summaries_are_non_empty(self):
        for summary in MeetingSummary.objects.all():
            self.assertTrue(summary.summary.strip())

    def test_action_items_mix_of_ai_and_manual(self):
        self.assertTrue(ActionItem.objects.filter(is_ai_generated=True).exists())
        self.assertTrue(ActionItem.objects.filter(is_ai_generated=False).exists())

    def test_action_items_mix_of_done_and_not_done(self):
        self.assertTrue(ActionItem.objects.filter(is_done=True).exists())
        self.assertTrue(ActionItem.objects.filter(is_done=False).exists())

    def test_seed_migration_is_idempotent_when_rerun_directly(self):
        """Simulates re-running `migrate` by invoking the migration's
        forward function a second time directly against the already-seeded
        test database - get_or_create / existence checks inside it must
        guard against duplicate rows."""
        import importlib

        from django.apps import apps as global_apps

        module = importlib.import_module("apps.meetings.migrations.0002_seed_demo_data")

        before_users = User.objects.count()
        before_meetings = Meeting.objects.count()
        before_summaries = MeetingSummary.objects.count()
        before_action_items = ActionItem.objects.count()

        module.seed_demo_data(global_apps, None)

        self.assertEqual(User.objects.count(), before_users)
        self.assertEqual(Meeting.objects.count(), before_meetings)
        self.assertEqual(MeetingSummary.objects.count(), before_summaries)
        self.assertEqual(ActionItem.objects.count(), before_action_items)
