from django.template.loader import render_to_string

from wagtail.admin.compare import ForeignObjectComparison
from wagtail.admin.edit_handlers import BaseChooserPanel

from .widgets import AdminImageChooser, AdminImageRenditionChooser


class ImageChooserPanel(BaseChooserPanel):
    object_type_name = "image"

    def widget_overrides(self):
        return {self.field_name: AdminImageChooser}

    def get_comparison_class(self):
        return ImageFieldComparison


class RenditionChooserPanel(ImageChooserPanel):

    def __init__(self, *args, crop=None, ratios=None,
                 default_ratio=None, disable_selection=False,
                 force_selection=False, post_processing_spec=None,
                 **kwargs):
        '''Create a panel that allows selecting and customizing an image.

            :param field_name:  the field this panel is rendering
            :param classname:   extra css classes to be added to the field
            :param help_text:   help_text to use (overrides field.help_text)
            :param heading:     heading to use (overrides field.title)
            :param crop:        a 4-tuple of cropping coordinates, it will
                                override the filter spec extracted from
                                rendition
            :param ratios:      a list of aspect ratios available (using
                                'width:height' format, or some text for
                                'no ratio')
            :param default_ratio:   aspect ratio selected by default
            :param force_selection: whether the widget forces a crop selection
            :param disable_selection: whether aspect ratio choices are disabled
                                      (this setting also causes
                                       force_selection=True)
            :param post_processing_spec:  additional processing to be applied
                                          to the selected rendition
        '''
        super().__init__(*args, **kwargs)

        # convert extra parameters into strings that will be used in templates
        if crop and len(crop) == 4:
            crop = ','.join(str(c) for c in crop)

        if ratios and not isinstance(ratios, str):
            ratios = ','.join(ratios)

        self.crop = crop
        self.ratios = ratios
        self.default_ratio = default_ratio
        self.disable_selection = disable_selection
        self.force_selection = force_selection
        self.post_processing_spec = post_processing_spec

    def widget_overrides(self):
        return {self.field_name: AdminImageRenditionChooser(panel=self)}

    def clone(self):
        return self.__class__(
            field_name=self.field_name,
            widget=self.widget if hasattr(self, 'widget') else None,
            heading=self.heading,
            classname=self.classname,
            help_text=self.help_text,
            extra_js=self.extra_js,
            crop=self.crop,
            ratios=self.ratios,
            default_ratio=self.default_ratio,
            disable_selection=self.disable_selection,
            force_selection=self.force_selection,
            post_processing_spec=self.post_processing_spec,
        )


class ImageFieldComparison(ForeignObjectComparison):
    def htmldiff(self):
        image_a, image_b = self.get_objects()

        return render_to_string("wagtailimages/widgets/compare.html", {
            'image_a': image_a,
            'image_b': image_b,
        })
