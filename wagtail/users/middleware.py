import pytz

from django.utils import timezone
from wagtail.wagtailusers.models import UserProfile


class TimezoneMiddleware(object):
    def process_request(self, request):
        tzname = None

        if request.user and not request.user.is_anonymous():
            up = UserProfile.get_for_user(request.user)
            tzname = up.timezone

        if tzname:
            timezone.activate(pytz.timezone(tzname))
        else:
            timezone.deactivate()
