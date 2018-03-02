import pytz

from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

from wagtail.users.models import UserProfile


class TimezoneMiddleware(MiddlewareMixin):
    def process_request(self, request):
        tzname = None

        if request.user and not request.user.is_anonymous:
            up = UserProfile.get_for_user(request.user)
            tzname = up.timezone

        if tzname:
            timezone.activate(pytz.timezone(tzname))
        else:
            timezone.deactivate()
