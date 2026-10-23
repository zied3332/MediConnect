"""
Notification service — the only entry point other modules should use.

    from notifications.services import notify
    notify(user, "Your appointment was confirmed.", "appointment", link="/appointments/3/")
"""

from .models import Notification


def notify(user, message, type=Notification.Type.SYSTEM, link=""):
    """Create and return an unread notification for `user`."""
    if type not in Notification.Type.values:
        raise ValueError(f"Unknown notification type: {type!r}")
    return Notification.objects.create(
        user=user,
        message=message[:500],
        type=type,
        link=link or "",
    )


def unread_count(user):
    if not user.is_authenticated:
        return 0
    return Notification.objects.filter(user=user, is_read=False).count()
