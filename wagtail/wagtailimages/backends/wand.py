from __future__ import absolute_import

from wand.image import Image
from wand.api import library

from wagtail.wagtailimages.backends.base import BaseImageBackend


class WandBackend(BaseImageBackend):
    def __init__(self, params):
        super(WandBackend, self).__init__(params)

    def open_image(self, input_file):
        image = Image(file=input_file)
        image.wand = library.MagickCoalesceImages(image.wand)
        return image

    def save_image(self, image, output, format):
        image.format = format
        image.compression_quality = self.quality
        image.save(file=output)

    def resize(self, image, size):
        new_image = image.clone()
        new_image.resize(size[0], size[1])
        return new_image

    def crop(self, image, crop_box):
        new_image = image.clone()
        new_image.crop(
            left=crop_box[0], top=crop_box[1], right=crop_box[2], bottom=crop_box[3]
        )
        return new_image

    def image_data_as_rgb(self, image):
        # Only return image data if this image is not animated
        if image.animation:
            return

        return 'RGB', image.make_blob('RGB')

    def crop_to_rectangle(self, image, rect):
        (original_width, original_height) = image.size
        (left, top, right, bottom) = rect

        # final dimensions should not exceed original dimensions
        left = max(0, left)
        top = max(0, top)
        right = min(original_width, right)
        bottom = min(original_height, bottom)

        if (left == right ==0 and right == original_width
                and bottom == original_height):
            return image

        new_image = image.clone()
        new_image.crop(left=left, top=top, right=right, bottom=bottom)
        return new_image
