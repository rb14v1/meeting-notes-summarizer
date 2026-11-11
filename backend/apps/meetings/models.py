from django.conf import settings
from django.db import models


class Meeting(models.Model):
    """A single meeting's pasted/typed freeform notes. Visible to every
    authenticated user (there's no per-user scoping in this app - any
    logged-in user can see all meetings) but only editable/deletable by its
    creator or an admin (see apps/meetings/permissions.py)."""

    title = models.CharField(max_length=255)
    meeting_date = models.DateField()
    raw_notes = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meetings"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-meeting_date", "-id"]

    def __str__(self):
        return self.title


class MeetingSummary(models.Model):
    """One-to-one with Meeting. Generated via apps.common.ai.summarize_meeting_notes
    and replaced (not appended to) on every re-summarize - see
    MeetingViewSet.summarize."""

    meeting = models.OneToOneField(Meeting, on_delete=models.CASCADE, related_name="summary")
    summary = models.TextField()
    generated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Summary for {self.meeting.title}"


class ActionItem(models.Model):
    """An action item belonging to a meeting. `is_ai_generated` tracks
    whether this row came from the last summarize call (True) or was added
    manually by a user (False) - only the AI-generated subset is cleared and
    replaced when a meeting is re-summarized; manually-added items and their
    done/edited state are preserved. Manual edits (description, assignee,
    is_done) work regardless of is_ai_generated."""

    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name="action_items")
    description = models.TextField()
    assignee = models.CharField(max_length=255, null=True, blank=True)
    is_done = models.BooleanField(default=False)
    is_ai_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.description[:60]
