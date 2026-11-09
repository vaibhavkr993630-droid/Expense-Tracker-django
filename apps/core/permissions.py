from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """
    Object-level permission: the object must belong to the requesting user.

    `has_object_permission` runs when a view calls `self.get_object()`. Views also scope their
    queryset to the user, so other people's objects are simply "not found" (404, which does not
    reveal that the id exists). This class is the second line of defence if a queryset is ever
    written without that scoping.
    """

    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id
