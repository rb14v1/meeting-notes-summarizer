from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.meetings.models import ActionItem, Meeting
from common.test_utils import auth_client, create_user


class ActionItemManualCRUDTests(APITestCase):
    def setUp(self):
        self.user = create_user(email="itemowner@example.com")
        self.client_ = auth_client(self.user)
        self.meeting = Meeting.objects.create(
            title="Weekly Sync", meeting_date="2026-01-01", raw_notes="notes", created_by=self.user,
        )

    def test_create_manual_action_item(self):
        url = reverse("meeting-action-items-list", args=[self.meeting.id])
        response = self.client_.post(url, {"description": "Send the follow-up email", "assignee": "Sam"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertFalse(response.data["is_ai_generated"])
        self.assertEqual(response.data["assignee"], "Sam")

    def test_create_manual_action_item_without_assignee(self):
        url = reverse("meeting-action-items-list", args=[self.meeting.id])
        response = self.client_.post(url, {"description": "Unassigned task"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIsNone(response.data["assignee"])

    def test_create_action_item_blank_description_rejected(self):
        url = reverse("meeting-action-items-list", args=[self.meeting.id])
        response = self.client_.post(url, {"description": "   "})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_action_items_for_meeting(self):
        ActionItem.objects.create(meeting=self.meeting, description="Item A")
        ActionItem.objects.create(meeting=self.meeting, description="Item B")
        url = reverse("meeting-action-items-list", args=[self.meeting.id])
        response = self.client_.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_toggle_is_done(self):
        item = ActionItem.objects.create(meeting=self.meeting, description="Toggle me", is_done=False)
        url = reverse("action-item-detail", args=[item.id])
        response = self.client_.patch(url, {"is_done": True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertTrue(item.is_done)

    def test_edit_description_and_assignee(self):
        item = ActionItem.objects.create(meeting=self.meeting, description="Old text")
        url = reverse("action-item-detail", args=[item.id])
        response = self.client_.patch(url, {"description": "New text", "assignee": "Jordan"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.description, "New text")
        self.assertEqual(item.assignee, "Jordan")

    def test_manual_edit_works_on_ai_generated_item(self):
        ai_item = ActionItem.objects.create(meeting=self.meeting, description="AI task", is_ai_generated=True)
        url = reverse("action-item-detail", args=[ai_item.id])
        response = self.client_.patch(url, {"is_done": True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ai_item.refresh_from_db()
        self.assertTrue(ai_item.is_done)
        # is_ai_generated is read-only and untouched by the edit.
        self.assertTrue(ai_item.is_ai_generated)

    def test_delete_action_item(self):
        item = ActionItem.objects.create(meeting=self.meeting, description="Delete me")
        url = reverse("action-item-detail", args=[item.id])
        response = self.client_.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ActionItem.objects.filter(id=item.id).exists())

    def test_delete_ai_generated_action_item(self):
        item = ActionItem.objects.create(meeting=self.meeting, description="AI task to delete", is_ai_generated=True)
        url = reverse("action-item-detail", args=[item.id])
        response = self.client_.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_action_item_endpoints_require_authentication(self):
        item = ActionItem.objects.create(meeting=self.meeting, description="Needs auth")
        url = reverse("action-item-detail", args=[item.id])
        response = self.client.patch(url, {"is_done": True})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
