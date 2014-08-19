from wagtail.wagtailadmin.edit_handlers import BaseChooserPanel


class BaseImageChooserPanel(BaseChooserPanel):
    field_template = "wagtailimages/edit_handlers/image_chooser_panel.html"
    object_type_name = "image"
    js_function_name = "createImageChooser"


def ImageChooserPanel(field_name, classname=''):
    return type('_ImageChooserPanel', (BaseImageChooserPanel,), {
        'field_name': field_name,
        'classname': classname,
    })


class BaseRenditionChooserPanel(BaseChooserPanel):
    field_template = "wagtailimages/edit_handlers/rendition_chooser_panel.html"
    object_type_name = "image"
    js_function_name = "createRenditionChooser"


def RenditionChooserPanel(field_name, classname=''):
    return type('_RenditionChooserPanel', (BaseRenditionChooserPanel,), {
        'field_name': field_name,
        'classname': classname,
    })
