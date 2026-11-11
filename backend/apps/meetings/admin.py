from django.contrib import admin

from apps.meetings.models import ActionItem, Meeting, MeetingSummary


class ActionItemInline(admin.TabularInline):
    model = ActionItem
    extra = 0


class MeetingSummaryInline(admin.StackedInline):
    model = MeetingSummary
    extra = 0


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ["title", "meeting_date", "created_by", "created_at"]
    list_filter = ["meeting_date"]
    search_fields = ["title", "raw_notes"]
    inlines = [MeetingSummaryInline, ActionItemInline]


@admin.register(ActionItem)
class ActionItemAdmin(admin.ModelAdmin):
    list_display = ["description", "meeting", "assignee", "is_done", "is_ai_generated"]
    list_filter = ["is_done", "is_ai_generated"]
