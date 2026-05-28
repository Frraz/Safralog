def unread_notifications(request):
    if not request.user.is_authenticated:
        return {"unread_notifications_count": 0, "unread_notifications": []}

    try:
        from apps.notifications.models import Notification
        unread = Notification.objects.filter(
            user=request.user, is_read=False
        ).order_by("-created_at")[:10]
        return {
            "unread_notifications_count": unread.count(),
            "unread_notifications": unread,
        }
    except Exception:
        return {"unread_notifications_count": 0, "unread_notifications": []}
