from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.meetings.models import Meeting
from common.test_utils import auth_client, create_user


class MeetingCRUDTests(APITestCase):
    def setUp(self):
        self.member = create_user(email="member1@example.com", role=User.Role.MEMBER)
        self.client_ = auth_client(self.member)

    def test_create_meeting(self):
        url = reverse("meeting-list")
        response = self.client_.post(url, {
            "title": "Design Review",
            "meeting_date": "2026-01-15",
            "raw_notes": "We reviewed the new design mockups.",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["created_by"]["id"], self.member.id)
        self.assertIsNone(response.data["summary"])
        self.assertEqual(response.data["action_items"], [])

    def test_create_meeting_requires_title(self):
        url = reverse("meeting-list")
        response = self.client_.post(url, {
            "title": "   ",
            "meeting_date": "2026-01-15",
            "raw_notes": "Notes.",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_meetings_shows_all_users_meetings(self):
        other = create_user(email="other1@example.com")
        Meeting.objects.create(title="Mine", meeting_date="2026-01-01", raw_notes="x", created_by=self.member)
        Meeting.objects.create(title="Theirs", meeting_date="2026-01-02", raw_notes="y", created_by=other)

        response = self.client_.get(reverse("meeting-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {m["title"] for m in response.data["results"]}
        self.assertIn("Mine", titles)
        self.assertIn("Theirs", titles)

    def test_retrieve_meeting(self):
        meeting = Meeting.objects.create(title="Standup", meeting_date="2026-01-01", raw_notes="x", created_by=self.member)
        response = self.client_.get(reverse("meeting-detail", args=[meeting.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Standup")

    def test_update_own_meeting(self):
        meeting = Meeting.objects.create(title="Old title", meeting_date="2026-01-01", raw_notes="x", created_by=self.member)
        response = self.client_.put(reverse("meeting-detail", args=[meeting.id]), {
            "title": "New title",
            "meeting_date": "2026-01-02",
            "raw_notes": "updated notes",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        meeting.refresh_from_db()
        self.assertEqual(meeting.title, "New title")

    def test_delete_own_meeting(self):
        meeting = Meeting.objects.create(title="Delete me", meeting_date="2026-01-01", raw_notes="x", created_by=self.member)
        response = self.client_.delete(reverse("meeting-detail", args=[meeting.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Meeting.objects.filter(id=meeting.id).exists())

    def test_unauthenticated_requests_rejected(self):
        response = self.client.get(reverse("meeting-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MeetingCrossUserPermissionTests(APITestCase):
    """Any authenticated user can see all meetings, but only the creator or
    an admin can edit/delete it."""

    def setUp(self):
        self.creator = create_user(email="creator@example.com", role=User.Role.MEMBER)
        self.other_member = create_user(email="other-member@example.com", role=User.Role.MEMBER)
        self.admin = create_user(email="admin-perm@example.com", role=User.Role.ADMIN)
        self.meeting = Meeting.objects.create(
            title="Confidential Planning", meeting_date="2026-01-01",
            raw_notes="secret notes", created_by=self.creator,
        )

    def test_other_member_can_read_meeting(self):
        client = auth_client(self.other_member)
        response = client.get(reverse("meeting-detail", args=[self.meeting.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_member_cannot_update_meeting(self):
        client = auth_client(self.other_member)
        response = client.put(reverse("meeting-detail", args=[self.meeting.id]), {
            "title": "Hijacked", "meeting_date": "2026-01-01", "raw_notes": "x",
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_member_cannot_delete_meeting(self):
        client = auth_client(self.other_member)
        response = client.delete(reverse("meeting-detail", args=[self.meeting.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Meeting.objects.filter(id=self.meeting.id).exists())

    def test_admin_can_update_other_users_meeting(self):
        client = auth_client(self.admin)
        response = client.patch(reverse("meeting-detail", args=[self.meeting.id]), {"title": "Edited by admin"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.meeting.refresh_from_db()
        self.assertEqual(self.meeting.title, "Edited by admin")

    def test_admin_can_delete_other_users_meeting(self):
        client = auth_client(self.admin)
        response = client.delete(reverse("meeting-detail", args=[self.meeting.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_creator_can_update_own_meeting(self):
        client = auth_client(self.creator)
        response = client.patch(reverse("meeting-detail", args=[self.meeting.id]), {"title": "Edited by creator"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
