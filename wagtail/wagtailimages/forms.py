from django import forms
from django.forms.models import modelform_factory
from django.utils.translation import ugettext as _

from wagtail.wagtailimages.models import get_image_model
from wagtail.wagtailimages.formats import get_image_formats
from wagtail.wagtailimages.fields import WagtailImageField


# Callback to allow us to override the default form field for the image file field
def formfield_for_dbfield(db_field, **kwargs):
    # Check if this is the file field
    if db_field.name == 'file':
        return WagtailImageField(**kwargs)

    # For all other fields, just call its formfield() method.
    return db_field.formfield(**kwargs)


def get_image_form(hide_file=False):
    widgets={
        'focal_point_x': forms.HiddenInput(attrs={'class': 'focal_point_x'}),
        'focal_point_y': forms.HiddenInput(attrs={'class': 'focal_point_y'}),
        'focal_point_width': forms.HiddenInput(attrs={'class': 'focal_point_width'}),
        'focal_point_height': forms.HiddenInput(attrs={'class': 'focal_point_height'}),
    }

    if hide_file:
        widgets['file'] = forms.HiddenInput()
    else:
        # set the 'file' widget to a FileInput rather than the default ClearableFileInput
        # so that when editing, we don't get the 'currently: ...' banner which is
        # a bit pointless here
        widgets['file'] = forms.FileInput()

    return modelform_factory(
        get_image_model(),
        formfield_callback=formfield_for_dbfield,
        widgets=widgets
    )


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
    closeness = forms.IntegerField(_("Closeness"), min_value=0, initial=0)


class HiddenNumberInput(forms.IntegerField):
    widget = forms.HiddenInput


class ImageCropperForm(forms.Form):
    """Form for selecting a cropped version of the image."""

    left = HiddenNumberInput(label='')
    top = HiddenNumberInput(label='')
    right = HiddenNumberInput(label='')
    bottom = HiddenNumberInput(label='')
    force_selection = forms.BooleanField(required=False, label='',
                                         widget=forms.HiddenInput())
    width = forms.IntegerField(required=False, label=_('Fit width'))
    height = forms.IntegerField(required=False, label=_('height'))

    ratios = ('1:1', '4:3', '16:9', '2:1', 'free')
    default_ratio = 'free'
    disable_selection = False
    post_processing_spec = None

    def __init__(self, *args, **kwargs):

        for name in ('ratios', 'default_ratio', 'disable_selection',
                     'post_processing_spec'):
            if name in kwargs:
                val = kwargs.pop(name)
                if val is not None:
                    setattr(self, name, val)

        if self.disable_selection:
            kwargs['initial'] = kwargs.get('initial') or {}
            kwargs['initial']['force_selection'] = True

        super(ImageCropperForm, self).__init__(*args, **kwargs)
