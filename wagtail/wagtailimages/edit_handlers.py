from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from __future__ import absolute_import, unicode_literals

from wagtail.wagtailadmin.edit_handlers import BaseChooserPanel
from .widgets import AdminImageChooser


class BaseImageChooserPanel(BaseChooserPanel):
    object_type_name = "image"

    @classmethod
    def widget_overrides(cls):
        return {cls.field_name: AdminImageChooser}


class ImageChooserPanel(object):
    def __init__(self, field_name, classname=''):
        self.field_name = field_name
        self.classname = classname


    def bind_to_model(self, model):
        return type(str('_ImageChooserPanel'), (BaseImageChooserPanel,), {
            'model': model,
            'field_name': self.field_name,
            'classname': self.classname,
        })


class BaseRenditionChooserPanel(BaseChooserPanel):
    field_template = "wagtailimages/edit_handlers/rendition_chooser_panel.html"
    object_type_name = "image"
    js_function_name = "createRenditionChooser"
    post_processing_spec = None

    def render_as_field(self, show_help_text=True):
        instance_obj = self.get_chosen_item()
        return mark_safe(render_to_string(self.field_template, {
            'field': self.bound_field,
            self.object_type_name: instance_obj,
            'is_chosen': bool(instance_obj),
            'show_help_text': show_help_text,
            'crop': self.crop,
            'ratios': self.ratios,
            'default_ratio': self.default_ratio,
            'disable_selection': self.disable_selection,
            'force_selection': self.force_selection,
            'post_processing_spec': self.post_processing_spec,
        }))


class RenditionChooserPanel(object):
    def __init__(self, field_name, classname='', help_text=None,
                       heading=None, crop=None, ratios=None,
                       default_ratio=None, disable_selection=False,
                       force_selection=False, post_processing_spec=None):
        '''Create a panel that ultimately allows selecting and customizing an image.

            :param field_name:  the field this panel is rendering
            :param classname:   extra css classes to be added to the field
            :param help_text:   help_text to use (overrides field.help_text)
            :param heading:     heading to use (overrides field.title)
            :param crop:        a 4-tuple of cropping coordinates, it will override
                                the filter spec extracted from rendition
            :param ratios:      a list of aspect ratios available (using
                                'width:height' format, or some text for 'no ratio')
            :param default_ratio:   aspect ratio selected by default
            :param force_selection:     whether the widget forces a crop selection
            :param disable_selection:   whether aspect ratio choices are disabled
                                        (this setting also causes
                                         force_selection=True)
            :param post_processing_spec:    additional processing to be applied to
                                            the selected rendition
        '''

        # convert extra parameters into strings that will be used in templates
        #
        if crop and len(crop) == 4:
            crop = ','.join(str(c) for c in crop)

        if ratios:
            ratios = ','.join(ratios)

        self.field_name = field_name
        self.classname = classname
        self.help_text = help_text
        self.heading = heading
        self.crop = crop
        self.ratios = ratios
        self.default_ratio = default_ratio
        self.disable_selection = disable_selection
        self.force_selection = force_selection
        self.post_processing_spec = post_processing_spec

    def bind_to_model(self, model):
        return type('_RenditionChooserPanel', (BaseRenditionChooserPanel,), {
            'model': model,
            'field_name': self.field_name,
            'classname': self.classname,
            'heading': self.heading,
            'help_text': self.help_text,
            'crop': self.crop,
            'ratios': self.ratios,
            'default_ratio': self.default_ratio,
            'disable_selection': self.disable_selection,
            'force_selection': self.force_selection,
            'post_processing_spec': self.post_processing_spec,
        })
