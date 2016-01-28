from __future__ import unicode_literals

from six import text_type, with_metaclass

try:
    # renamed util -> utils in Django 1.7; try the new name first
    from django.forms.utils import flatatt
except ImportError:
    from django.forms.util import flatatt

from django.conf import settings
from django.forms import MediaDefiningClass
from django.utils.text import slugify
from django.utils.html import format_html, format_html_join

from wagtail.wagtailcore import hooks


class MenuItem(with_metaclass(MediaDefiningClass)):
    def __init__(self, label, url, name=None, classnames='', attrs=None, order=1000):
        self.label = label
        self.url = url
        self.classnames = classnames
        self.name = (name or slugify(text_type(label)))
        self.order = order

        if attrs:
            self.attr_string = flatatt(attrs)
        else:
            self.attr_string = ""

    def is_shown(self, request):
        """
        Whether this menu item should be shown for the given request; permission
        checks etc should go here. By default, menu items are shown all the time
        """
        return True

    def render_html(self):
        return format_html(
            """<li class="menu-{0}"><a href="{1}" class="{2}"{3}>{4}</a></li>""",
            self.name, self.url, self.classnames, self.attr_string, self.label)


class PageActionButton(object):
    def __init__(self, label, url, classnames='button button-small'):
        self.label = label
        self.url = url
        self.classnames = classnames

    def render_html(self, page=None):
        url = self.url

        if callable(url):
            # if the url is callable, assume it takes a page as only parameter
            #
            url = url(page)

        return format_html(
            """<li><a href="{0}" class="{1}">{2}</a></li>""",
            url, self.classnames, self.label)


_master_menu_item_list = None
def get_master_menu_item_list():
    """
    Return the list of menu items registered with the 'register_admin_menu_item' hook.
    This is the "master list" because the final admin menu may vary per request
    according to the value of is_shown() and the construct_main_menu hook.
    """
    global _master_menu_item_list
    if _master_menu_item_list is None:
        _master_menu_item_list = [fn() for fn in hooks.get_hooks('register_admin_menu_item')]

    return _master_menu_item_list
