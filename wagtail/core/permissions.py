from wagtail.core.models import Collection, Site
from wagtail.core.models import UserPagePermissionsProxy
from wagtail.core.permission_policies import ModelPermissionPolicy

site_permission_policy = ModelPermissionPolicy(Site)
collection_permission_policy = ModelPermissionPolicy(Collection)


def user_can_edit_any_pages(user):
    if not user.is_active:
        return False
    if user.is_superuser:
        return True
    else:
        return bool(UserPagePermissionsProxy(user).permissions)
