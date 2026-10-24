from .services import unread_count


def unread_notifications(request):
    """Expose the unread count to every template (topbar bell)."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {"unread_notifications_count": unread_count(user)}
