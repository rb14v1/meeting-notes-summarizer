from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.meetings.views import (
    ActionItemDetailView,
    MeetingActionItemListCreateView,
    MeetingViewSet,
)

router = DefaultRouter()
router.register(r"meetings", MeetingViewSet, basename="meeting")

urlpatterns = [
    path(
        "meetings/<int:meeting_pk>/action-items/",
        MeetingActionItemListCreateView.as_view(),
        name="meeting-action-items-list",
    ),
    path("action-items/<int:pk>/", ActionItemDetailView.as_view(), name="action-item-detail"),
] + router.urls
