from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user)
    page = Paginator(notifications, 15).get_page(request.GET.get("page"))
    return render(
        request,
        "notifications/list.html",
        {
            "page_title": "Notifications",
            "dashboard_role": request.user.role,
            "active_nav": "notifications",
            "page_obj": page,
            "has_unread": notifications.filter(is_read=False).exists(),
        },
    )


@login_required
@require_POST
def mark_read(request, pk):
    """Mark one notification as read, then open its link (internal links only)."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])

    link = notification.link
    if link and url_has_allowed_host_and_scheme(
        link, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(link)
    return redirect("notifications:list")


@login_required
@require_POST
def mark_all_read(request):
    updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, f"{updated} notification(s) marked as read.")
    return redirect("notifications:list")


@login_required
@require_POST
def delete_notification(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.delete()
    messages.success(request, "Notification deleted.")
    return redirect("notifications:list")
