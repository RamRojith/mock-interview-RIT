from django.shortcuts import redirect, render
from django.contrib import messages

from stock_management.decorators import stock_management
from user_accounts.decorators import check_permission
from stock_management.models import Notification
from stock_management.views.stock_common import get_logged_in_faculty


@stock_management
@check_permission("notifications")
def notifications(request):
    faculty = get_logged_in_faculty(request)
    if faculty:
        qs = Notification.objects.filter(recipient=faculty).order_by("-id")
        unread = qs.filter(is_read=False).count()   # count on the UNSLICED queryset
        items = qs[:100]
    else:
        items = Notification.objects.none()
        unread = 0
    return render(request, "stock_management/notifications/notifications.html", {
        "items": items,
        "unread": unread,
    })


@stock_management
def notifications_mark_read(request):
    faculty = get_logged_in_faculty(request)
    if request.method == "POST" and faculty:
        Notification.objects.filter(recipient=faculty, is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
    return redirect("notifications")
