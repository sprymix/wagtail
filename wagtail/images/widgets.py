import json

from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from wagtail.admin.widgets import AdminChooser
from wagtail.images import get_image_model
from wagtail.images.models import UserRendition


class AdminImageChooser(AdminChooser):
    choose_one_text = _('Choose an image')
    choose_another_text = _('Change image')
    link_to_chosen_text = _('Edit this image')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.image_model = get_image_model()

    def render_html(self, name, value, attrs):
        instance, value = self.get_instance_and_id(self.image_model, value)
        original_field_html = super().render_html(name, value, attrs)

        return render_to_string("wagtailimages/widgets/image_chooser.html", {
            'widget': self,
            'original_field_html': original_field_html,
            'attrs': attrs,
            'value': value,
            'image': instance,
        })

    def render_js_init(self, id_, name, value):
        return "createImageChooser({0});".format(json.dumps(id_))


class AdminImageRenditionChooser(AdminChooser):
    choose_one_text = _('Choose an image')
    choose_another_text = _('Change image')
    link_to_chosen_text = _('Edit this image')

    def __init__(self, panel, **kwargs):
        super().__init__(**kwargs)
        self.panel = panel

    def render_html(self, name, value, attrs):
        instance, value = self.get_instance_and_id(UserRendition, value)
        original_field_html = super().render_html(name, value, attrs)

        tpl = "wagtailimages/widgets/image_rendition_chooser.html"
        return render_to_string(tpl, {
            'widget': self,
            'original_field_html': original_field_html,
            'attrs': attrs,
            'value': value,
            'image': instance,
            'crop': self.panel.crop,
            'ratios': self.panel.ratios,
            'default_ratio': self.panel.default_ratio,
            'disable_selection': self.panel.disable_selection,
            'force_selection': self.panel.force_selection,
            'post_processing_spec': self.panel.post_processing_spec,
        })

    def render_js_init(self, id_, name, value):
        return "createRenditionChooser({0});".format(json.dumps(id_))
