from django import forms
from django.forms.models import modelform_factory
from django.utils.translation import ugettext as _

from wagtail.wagtailimages.models import get_image_model
from wagtail.wagtailimages.formats import get_image_formats


def get_image_form():
    return modelform_factory(
        get_image_model(),
        # set the 'file' widget to a FileInput rather than the default ClearableFileInput
        # so that when editing, we don't get the 'currently: ...' banner which is
        # a bit pointless here
        widgets={'file': forms.FileInput()})


def get_image_form_for_multi():
    # exclude the file widget
    return modelform_factory(get_image_model(), exclude=('file',))


class ImageInsertionForm(forms.Form):
    """
    Form for selecting parameters of the image (e.g. format) prior to insertion
    into a rich text area
    """
    format = forms.ChoiceField(
        choices=[(format.name, format.label) for format in get_image_formats()],
        widget=forms.RadioSelect
    )
    alt_text = forms.CharField()


class URLGeneratorForm(forms.Form):
    filter_method = forms.ChoiceField(
        label=_("Filter"),
        choices=(
            ('original', _("Original size")),
            ('width', _("Resize to width")),
            ('height', _("Resize to height")),
            ('min', _("Resize to min")),
            ('max', _("Resize to max")),
            ('fill', _("Resize to fill")),
        ),
    )
    width = forms.IntegerField(_("Width"), min_value=0)
    height = forms.IntegerField(_("Height"), min_value=0)


class HiddenNumberInput(forms.IntegerField):
    widget = forms.HiddenInput


class ImageCropperForm(forms.Form):
    """Form for selecting a cropped version of the image."""

    left = HiddenNumberInput()
    top = HiddenNumberInput()
    right = HiddenNumberInput()
    bottom = HiddenNumberInput()
    force_selection = forms.BooleanField(widget=forms.HiddenInput())

    ratios = ('1:1', '4:3', '16:9', '2:1', 'free')
    default_ratio = 'free'
    disable_selection = False

    def __init__(self, *args, **kwargs):

        for name in ('ratios', 'default_ratio', 'disable_selection'):
            if name in kwargs:
                val = kwargs.pop(name)
                if val is not None:
                    setattr(self, name, val)

        if self.disable_selection:
            kwargs['initial'] = kwargs.get('initial') or {}
            kwargs['initial']['force_selection'] = True

        super(ImageCropperForm, self).__init__(*args, **kwargs)
