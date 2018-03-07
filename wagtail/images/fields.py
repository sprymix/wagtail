import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms.fields import ImageField
from django.template.defaultfilters import filesizeformat
from django.utils.translation import ugettext_lazy as _

ALLOWED_EXTENSIONS = ['gif', 'jpg', 'jpeg', 'png']
SUPPORTED_FORMATS_TEXT = _("GIF, JPEG, PNG")

INVALID_IMAGE_ERROR = _(
    "Not a supported image format. Supported formats: %s."
) % SUPPORTED_FORMATS_TEXT

INVALID_IMAGE_KNOWN_FORMAT_ERROR = _(
    "Not a valid %s image."
)

MAX_UPLOAD_SIZE = getattr(settings, 'WAGTAILIMAGES_MAX_UPLOAD_SIZE', 10 * 1024 * 1024)

if MAX_UPLOAD_SIZE is not None:
    MAX_UPLOAD_SIZE_TEXT = filesizeformat(MAX_UPLOAD_SIZE)

    FILE_TOO_LARGE_ERROR = _(
        "This file is too big. Maximum filesize %s."
    ) % (MAX_UPLOAD_SIZE_TEXT, )

    FILE_TOO_LARGE_KNOWN_SIZE_ERROR = _(
        "This file is too big (%%s). Maximum filesize %s."
    ) % (MAX_UPLOAD_SIZE_TEXT, )

    IMAGE_FIELD_HELP_TEXT = _(
        "Supported formats: %s. Maximum filesize: %s."
    ) % (SUPPORTED_FORMATS_TEXT, MAX_UPLOAD_SIZE_TEXT, )
else:
    MAX_UPLOAD_SIZE_TEXT = ""
    FILE_TOO_LARGE_ERROR = ""
    FILE_TOO_LARGE_KNOWN_SIZE_ERROR = ""

    IMAGE_FIELD_HELP_TEXT = _(
        "Supported formats: %s."
    ) % (SUPPORTED_FORMATS_TEXT, )


class WagtailImageField(ImageField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get max upload size from settings
        self.max_upload_size = MAX_UPLOAD_SIZE
        max_upload_size_text = filesizeformat(self.max_upload_size)

        # Help text
        self.help_text = IMAGE_FIELD_HELP_TEXT

        # Error messages
        self.error_messages['invalid_image'] = INVALID_IMAGE_ERROR
        self.error_messages['invalid_image_known_format'] = \
            INVALID_IMAGE_KNOWN_FORMAT_ERROR
        self.error_messages['file_too_large'] = FILE_TOO_LARGE_KNOWN_SIZE_ERROR
        self.error_messages['file_too_large_unknown_size'] = \
            FILE_TOO_LARGE_ERROR

    def check_image_file_format(self, f):
        # Check file extension
        extension = os.path.splitext(f.name)[1].lower()[1:]

        if extension not in ALLOWED_EXTENSIONS:
            raise ValidationError(self.error_messages['invalid_image'], code='invalid_image')

        image_format = extension.upper()
        if image_format == 'JPG':
            image_format = 'JPEG'

        internal_image_format = f.image.format.upper()
        if internal_image_format == 'MPO':
            internal_image_format = 'JPEG'

        # Check that the internal format matches the extension
        # It is possible to upload PSD files if their extension is set to jpg, png or gif. This should catch them out
        if internal_image_format != image_format:
            raise ValidationError(self.error_messages['invalid_image_known_format'] % (
                image_format,
            ), code='invalid_image_known_format')

    def check_image_file_size(self, f):
        # Upload size checking can be disabled by setting max upload size to None
        if self.max_upload_size is None:
            return

        # Check the filesize
        if f.size > self.max_upload_size:
            raise ValidationError(self.error_messages['file_too_large'] % (
                filesizeformat(f.size),
            ), code='file_too_large')

    def to_python(self, data):
        f = super().to_python(data)

        if f is not None:
            self.check_image_file_size(f)
            self.check_image_file_format(f)

        return f
