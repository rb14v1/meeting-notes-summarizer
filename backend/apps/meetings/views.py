from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.ai import summarize_meeting_notes
from apps.meetings.models import ActionItem, Meeting, MeetingSummary
from apps.meetings.permissions import IsMeetingCreatorOrAdminForWrite
from apps.meetings.serializers import ActionItemSerializer, MeetingSerializer


class MeetingViewSet(viewsets.ModelViewSet):
    """Any authenticated user can see every meeting. Only the creator or an
    admin can update/delete a meeting - enforced by
    IsMeetingCreatorOrAdminForWrite.has_object_permission."""

    serializer_class = MeetingSerializer
    permission_classes = [permissions.IsAuthenticated, IsMeetingCreatorOrAdminForWrite]

    def get_queryset(self):
        return (
            Meeting.objects.all()
            .select_related("created_by")
            .prefetch_related("action_items")
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def summarize(self, request, pk=None):
        """Runs the single AI chat-completion call (apps.common.ai) against
        this meeting's raw_notes, then:
        - creates or replaces (never appends to) the MeetingSummary
        - deletes only the AI-generated ActionItems and recreates them from
          the fresh AI output; manually-added ActionItems are untouched.
        """
        meeting = self.get_object()
        result = summarize_meeting_notes(meeting.raw_notes)

        MeetingSummary.objects.update_or_create(
            meeting=meeting, defaults={"summary": result["summary"]}
        )

        meeting.action_items.filter(is_ai_generated=True).delete()
        ActionItem.objects.bulk_create([
            ActionItem(meeting=meeting, description=description, is_ai_generated=True)
            for description in result["action_items"]
        ])

        # Re-fetch so the response reflects the replaced summary/action
        # items rather than any stale prefetched/cached relations.
        fresh_meeting = self.get_queryset().get(pk=meeting.pk)
        serializer = self.get_serializer(fresh_meeting)
        return Response(serializer.data)


class MeetingActionItemListCreateView(generics.ListCreateAPIView):
    """GET: all action items for a meeting. POST: manually add one
    (is_ai_generated is always False for manually-created items)."""

    serializer_class = ActionItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_meeting(self):
        return get_object_or_404(Meeting, pk=self.kwargs["meeting_pk"])

    def get_queryset(self):
        return ActionItem.objects.filter(meeting=self.get_meeting())

    def perform_create(self, serializer):
        serializer.save(meeting=self.get_meeting(), is_ai_generated=False)


class ActionItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    """PATCH to toggle is_done / edit description & assignee, DELETE to
    remove. Works regardless of is_ai_generated - manual edits are always
    allowed on both AI-generated and manually-added action items."""

    queryset = ActionItem.objects.all()
    serializer_class = ActionItemSerializer
    permission_classes = [permissions.IsAuthenticated]
