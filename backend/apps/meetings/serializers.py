from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.meetings.models import ActionItem, Meeting, MeetingSummary


class MeetingSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingSummary
        fields = ["id", "summary", "generated_at"]
        read_only_fields = fields


class ActionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionItem
        fields = ["id", "meeting", "description", "assignee", "is_done", "is_ai_generated", "created_at"]
        read_only_fields = ["id", "meeting", "is_ai_generated", "created_at"]

    def validate_description(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Description cannot be blank.")
        return value


class MeetingSerializer(serializers.ModelSerializer):
    created_by = UserBriefSerializer(read_only=True)
    summary = serializers.SerializerMethodField()
    action_items = ActionItemSerializer(many=True, read_only=True)

    class Meta:
        model = Meeting
        fields = [
            "id", "title", "meeting_date", "raw_notes",
            "created_by", "created_at", "summary", "action_items",
        ]
        read_only_fields = ["id", "created_by", "created_at"]

    def get_summary(self, obj):
        try:
            return MeetingSummarySerializer(obj.summary).data
        except MeetingSummary.DoesNotExist:
            return None

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Title cannot be blank.")
        return value
