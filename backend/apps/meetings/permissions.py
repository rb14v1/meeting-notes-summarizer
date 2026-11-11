from rest_framework import permissions


class IsMeetingCreatorOrAdminForWrite(permissions.BasePermission):
    """Any authenticated user may list/retrieve any meeting and trigger
    summarize on it. Only the meeting's creator or an admin may update or
    delete the meeting itself."""

    restricted_actions = {"update", "partial_update", "destroy"}

    def has_object_permission(self, request, view, obj):
        if getattr(view, "action", None) not in self.restricted_actions:
            return True
        user = request.user
        return obj.created_by_id == user.id or user.is_admin
