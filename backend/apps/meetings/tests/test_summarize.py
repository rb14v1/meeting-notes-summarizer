from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.meetings.models import ActionItem, Meeting, MeetingSummary
from common.test_utils import auth_client, create_user


class SummarizeEndpointTests(APITestCase):
    def setUp(self):
        self.user = create_user(email="summarizer@example.com")
        self.client_ = auth_client(self.user)
        self.meeting = Meeting.objects.create(
            title="Planning Sync",
            meeting_date="2026-01-01",
            raw_notes="We discussed the launch timeline. Bob will confirm vendor pricing by Friday.",
            created_by=self.user,
        )

    def test_summarize_creates_summary_and_action_items(self):
        url = reverse("meeting-summarize", args=[self.meeting.id])
        response = self.client_.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIsNotNone(response.data["summary"])
        self.assertTrue(MeetingSummary.objects.filter(meeting=self.meeting).exists())
        self.assertTrue(ActionItem.objects.filter(meeting=self.meeting, is_ai_generated=True).exists())
        self.assertGreater(len(response.data["action_items"]), 0)

    def test_resummarize_replaces_summary_not_duplicates(self):
        url = reverse("meeting-summarize", args=[self.meeting.id])
        self.client_.post(url)
        self.assertEqual(MeetingSummary.objects.filter(meeting=self.meeting).count(), 1)
        self.client_.post(url)
        self.assertEqual(MeetingSummary.objects.filter(meeting=self.meeting).count(), 1)

    def test_resummarize_preserves_manually_added_action_items(self):
        url = reverse("meeting-summarize", args=[self.meeting.id])
        self.client_.post(url)

        manual_item = ActionItem.objects.create(
            meeting=self.meeting, description="Manually added task",
            assignee="Carol", is_ai_generated=False,
        )

        response = self.client_.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(ActionItem.objects.filter(id=manual_item.id).exists())
        descriptions = [item["description"] for item in response.data["action_items"]]
        self.assertIn("Manually added task", descriptions)

    def test_resummarize_replaces_only_ai_generated_items(self):
        url = reverse("meeting-summarize", args=[self.meeting.id])
        self.client_.post(url)
        first_ai_ids = set(
            ActionItem.objects.filter(meeting=self.meeting, is_ai_generated=True).values_list("id", flat=True)
        )
        manual_item = ActionItem.objects.create(
            meeting=self.meeting, description="Keep me", is_ai_generated=False,
        )

        self.client_.post(url)

        second_ai_ids = set(
            ActionItem.objects.filter(meeting=self.meeting, is_ai_generated=True).values_list("id", flat=True)
        )
        # AI-generated rows were deleted and recreated (new ids / same text).
        self.assertTrue(first_ai_ids.isdisjoint(second_ai_ids))
        # The manual item's own row is untouched.
        self.assertTrue(ActionItem.objects.filter(id=manual_item.id, description="Keep me").exists())

    def test_resummarize_with_same_notes_produces_same_stub_output_twice(self):
        """Determinism check at the HTTP layer: summarizing, deleting the
        result, then summarizing again from the same raw_notes gives the
        same summary text and action item descriptions both times."""
        url = reverse("meeting-summarize", args=[self.meeting.id])
        first_response = self.client_.post(url)
        first_summary = first_response.data["summary"]["summary"]
        first_descriptions = [item["description"] for item in first_response.data["action_items"]]

        second_response = self.client_.post(url)
        second_summary = second_response.data["summary"]["summary"]
        second_descriptions = [item["description"] for item in second_response.data["action_items"]]

        self.assertEqual(first_summary, second_summary)
        self.assertEqual(first_descriptions, second_descriptions)

    def test_summarize_requires_authentication(self):
        url = reverse("meeting-summarize", args=[self.meeting.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_summarize_accessible_to_any_authenticated_user(self):
        """Unlike edit/delete, summarize is not restricted to the meeting's
        creator or an admin - any authenticated user can trigger it, since
        meetings are visible to the whole team."""
        other_user = create_user(email="other-summarizer@example.com")
        client = auth_client(other_user)
        url = reverse("meeting-summarize", args=[self.meeting.id])
        response = client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
