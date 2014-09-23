import os.path
import re
import hashlib

from six import BytesIO

from taggit.managers import TaggableManager

from django.core.files import File
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.db import models
from django.db.models.signals import pre_delete, pre_save
from django.dispatch.dispatcher import receiver
from django.utils.safestring import mark_safe
from django.utils.html import escape, format_html_join
from django.conf import settings
from django.utils.translation import ugettext_lazy  as _
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.core.urlresolvers import reverse

from unidecode import unidecode

from wagtail.wagtailadmin.taggable import TagSearchable
from wagtail.wagtailimages.backends import get_image_backend
from wagtail.wagtailsearch import indexed
from wagtail.wagtailimages.utils.validators import validate_image_format
from wagtail.wagtailimages.utils.focal_point import FocalPoint
from wagtail.wagtailimages.utils.feature_detection import FeatureDetector, opencv_available
from wagtail.wagtailadmin.utils import get_object_usage


def _generate_output_filename(input_filename, filter_spec, focal_point_key='focus-none',
                              max_len=80):
    input_filename_parts = os.path.basename(input_filename).split('.')
    filename_without_extension = '.'.join(input_filename_parts[:-1])
    filename_extension = input_filename_parts[-1]

    if focal_point_key == 'focus-none':
        focal_point_key = ''

    # we want to condense arbitrarily long specs into a finite string
    #
    spec_hash = hashlib.sha1(filter_spec).hexdigest()
    extra_name_length = (len(spec_hash) + len(filename_extension)
                            + len(focal_point_key)
                            + 3)

    if extra_name_length >= max_len:
        raise RuntimeError('image file path is too long: {}'.format(input_filename))

    # trim filename base so that we're well under 100 chars
    filename_without_extension = filename_without_extension[:max_len - extra_name_length]
    if focal_point_key:
        output_filename_parts = [filename_without_extension, focal_point_key,
                                 spec_hash, filename_extension]
    else:
        output_filename_parts = [filename_without_extension,
                                 spec_hash, filename_extension]

    output_filename = '.'.join(output_filename_parts)
    return output_filename


def _rendition_for_missing_image(rendition_cls, image):
    '''Provide dummy rendition for missing image files.

    It's fairly routine for people to pull down remote databases to
    their local dev versions without retrieving the corresponding
    image files. In such a case, we would get an IOError at the point
    where we try to create the resized version of a non-existent
    image. Since this is a bit catastrophic for a missing image, we'll
    substitute a dummy Rendition object so that we just output a
    broken link instead.
    '''
    rendition = rendition_cls(image=image, width=0, height=0)
    rendition.file.name = 'not-found'
    return rendition


@python_2_unicode_compatible
class AbstractImage(models.Model, TagSearchable):
    title = models.CharField(max_length=255, verbose_name=_('Title') )

    def get_upload_to(self, filename):
        folder_name = 'original_images'
        filename = self.file.field.storage.get_valid_name(filename)

        # do a unidecode in the filename and then
        # replace non-ascii characters in filename with _ , to sidestep issues with filesystem encoding
        filename = "".join((i if ord(i) < 128 else '_') for i in unidecode(filename))

        while len(os.path.join(folder_name, filename)) >= 95:
            prefix, dot, extension = filename.rpartition('.')
            filename = prefix[:-1] + dot + extension
        return os.path.join(folder_name, filename)

    file = models.ImageField(verbose_name=_('File'), upload_to=get_upload_to, width_field='width', height_field='height', validators=[validate_image_format])
    width = models.IntegerField(editable=False)
    height = models.IntegerField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, editable=False)

    tags = TaggableManager(blank=True, verbose_name=_('Tags'),
            help_text=_('To enter multi-word tags, use double quotes: "some tag".'))

    focal_point_x = models.PositiveIntegerField(null=True, editable=False)
    focal_point_y = models.PositiveIntegerField(null=True, editable=False)
    focal_point_width = models.PositiveIntegerField(null=True, editable=False)
    focal_point_height = models.PositiveIntegerField(null=True, editable=False)

    def get_usage(self):
        return get_object_usage(self)

    @property
    def usage_url(self):
        return reverse('wagtailimages_image_usage',
                       args=(self.id,))

    search_fields = TagSearchable.search_fields + (
        indexed.FilterField('uploaded_by_user'),
    )

    def __str__(self):
        return self.title

    @property
    def focal_point(self):
        if self.focal_point_x is not None and \
           self.focal_point_y is not None and \
           self.focal_point_width is not None and \
           self.focal_point_height is not None:
            return FocalPoint(
                self.focal_point_x,
                self.focal_point_y,
                width=self.focal_point_width,
                height=self.focal_point_height,
            )

    @focal_point.setter
    def focal_point(self, focal_point):
        if focal_point is not None:
            self.focal_point_x = focal_point.x
            self.focal_point_y = focal_point.y
            self.focal_point_width = focal_point.width
            self.focal_point_height = focal_point.height
        else:
            self.focal_point_x = None
            self.focal_point_y = None
            self.focal_point_width = None
            self.focal_point_height = None

    def get_suggested_focal_point(self, backend_name='default'):
        backend = get_image_backend(backend_name)
        image_file = self.file.file

        # Make sure image is open and seeked to the beginning
        image_file.open('rb')
        image_file.seek(0)

        # Load the image
        image = backend.open_image(self.file.file)
        image_data = backend.image_data_as_rgb(image)

        # Make sure we have image data
        # If the image is animated, image_data_as_rgb will return None
        if image_data is None:
            return

        # Use feature detection to find a focal point
        feature_detector = FeatureDetector(image.size, image_data[0], image_data[1])
        focal_point = feature_detector.get_focal_point()

        # Add 20% extra room around the edge of the focal point
        if focal_point:
            focal_point.width *= 1.20
            focal_point.height *= 1.20

        return focal_point

    def get_rendition(self, filter):
        if not hasattr(filter, 'process_image'):
            # assume we've been passed a filter spec string, rather than a Filter object
            # TODO: keep an in-memory cache of filters, to avoid a db lookup
            filter, created = Filter.objects.get_or_create(spec=filter)

        try:
            if self.focal_point:
                rendition = self.renditions.get(
                    filter=filter,
                    focal_point_key=self.focal_point.get_key(),
                )
            else:
                rendition = self.renditions.get(
                    filter=filter,
                    focal_point_key='',
                )
        except ObjectDoesNotExist:
            file_field = self.file

            # If we have a backend attribute then pass it to process
            # image - else pass 'default'
            backend_name = getattr(self, 'backend', 'default')

            try:
                # CDN drivers are buggy and fail to raise proper exceptions
                # on absence of files.
                if not file_field.storage.exists(file_field.file.name):
                    raise IOError('file not found')

                generated_image = filter.process_image(file_field.file,
                                            backend_name=backend_name,
                                            focal_point=self.focal_point)

                # generate new filename derived from old one, inserting the
                # filter spec and focal point key before the extension
                if self.focal_point is not None:
                    focal_point_key = "focus-" + self.focal_point.get_key()
                else:
                    focal_point_key = "focus-none"

                output_filename = _generate_output_filename(
                                        file_field.file.name, filter.spec,
                                        focal_point_key)

                generated_image_file = File(generated_image,
                                            name=output_filename)
            except IOError:
                return _rendition_for_missing_image(self.renditions.model, self)

            if self.focal_point:
                rendition, created = self.renditions.get_or_create(
                    filter=filter,
                    focal_point_key=self.focal_point.get_key(),
                    defaults={'file': generated_image_file}
                )
            else:
                rendition, created = self.renditions.get_or_create(
                    filter=filter,
                    focal_point_key='',
                    defaults={'file': generated_image_file}
                )

        return rendition

    def get_user_rendition(self, filter):
        if not hasattr(filter, 'process_image'):
            # assume we've been passed a filter spec string, rather than a
            # Filter object TODO: keep an in-memory cache of filters, to avoid a
            # db lookup
            filter, created = Filter.objects.get_or_create(spec=filter)

        try:
            rendition = self.user_renditions.get(filter=filter)
        except ObjectDoesNotExist:
            file_field = self.file

            # If we have a backend attribute then pass it to process
            # image - else pass 'default'
            backend_name = getattr(self, 'backend', 'default')
            try:
                # CDN drivers are buggy and fail to raise proper exceptions
                # on absence of files.
                if not file_field.storage.exists(file_field.file.name):
                    raise IOError('file not found')

                generated_image = filter.process_image(
                                        file_field.file,
                                        backend_name=backend_name)

                output_filename = _generate_output_filename(
                                        file_field.file.name, filter.spec)

                generated_image_file = File(generated_image,
                                            name=output_filename)
            except IOError:
                return _rendition_for_missing_image(self.user_renditions.model,
                                                    self)

            rendition, created = self.user_renditions.get_or_create(
                filter=filter, defaults={'file': generated_image_file})

        return rendition

    def is_portrait(self):
        return (self.width < self.height)

    def is_landscape(self):
        return (self.height < self.width)

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    @property
    def default_alt_text(self):
        # by default the alt text field (used in rich text insertion) is populated
        # from the title. Subclasses might provide a separate alt field, and
        # override this
        return self.title

    def is_editable_by_user(self, user):
        if user.has_perm('wagtailimages.change_image'):
            # user has global permission to change images
            return True
        elif user.has_perm('wagtailimages.add_image') and self.uploaded_by_user == user:
            # user has image add permission, which also implicitly provides permission to edit their own images
            return True
        else:
            return False

    class Meta:
        abstract = True


class Image(AbstractImage):
    pass


# Do smartcropping calculations when user saves an image without a focal point
@receiver(pre_save, sender=Image)
def image_feature_detection(sender, instance, **kwargs):
    if getattr(settings, 'WAGTAILIMAGES_FEATURE_DETECTION_ENABLED', False):
        if not opencv_available:
            raise ImproperlyConfigured("pyOpenCV could not be found.")

        # Make sure the image doesn't already have a focal point
        if instance.focal_point is None:
            # Set the focal point
            instance.focal_point = instance.get_suggested_focal_point()


# Receive the pre_delete signal and delete the file associated with the model instance.
@receiver(pre_delete, sender=Image)
def image_delete(sender, instance, **kwargs):
    # Pass false so FileField doesn't save the model.
    instance.file.delete(False)


def get_image_model():
    from django.conf import settings
    from django.db.models import get_model

    try:
        app_label, model_name = settings.WAGTAILIMAGES_IMAGE_MODEL.split('.')
    except AttributeError:
        return Image
    except ValueError:
        raise ImproperlyConfigured("WAGTAILIMAGES_IMAGE_MODEL must be of the form 'app_label.model_name'")

    image_model = get_model(app_label, model_name)
    if image_model is None:
        raise ImproperlyConfigured("WAGTAILIMAGES_IMAGE_MODEL refers to model '%s' that has not been installed" % settings.WAGTAILIMAGES_IMAGE_MODEL)
    return image_model


class Filter(models.Model):
    """
    Represents an operation that can be applied to an Image to produce a rendition
    appropriate for final display on the website. Usually this would be a resize operation,
    but could potentially involve colour processing, etc.
    """
    spec = models.CharField(max_length=255, db_index=True)

    OPERATION_NAMES = {
        'max': 'resize_to_max',
        'min': 'resize_to_min',
        'width': 'resize_to_width',
        'height': 'resize_to_height',
        'fill': 'resize_to_fill',
        'original': 'no_operation',
        'crop': 'crop_to_rectangle',
        'forcewidth': 'force_resize_to_width',
        'forceheight': 'force_resize_to_height',
        'forcefit': 'force_resize_to_fit',
    }

    class InvalidFilterSpecError(ValueError):
        pass

    def __init__(self, *args, **kwargs):
        super(Filter, self).__init__(*args, **kwargs)
        self.method = None  # will be populated when needed, by parsing the spec string

    def _parse_spec_string(self, spec=None):
        # parse the spec string and save the results to
        # self.method_name and self.method_arg. There are various possible
        # formats to match against:
        # 'original'
        # 'width-200'
        # 'max-320x200'
        # 'crop-10,10:50,50'
        #
        # any format may be combined with another one by '|'
        # e.g. 'crop-50,50:150,150|max-50x50'

        if spec is None:
            spec = self.spec

        result = []
        for spec_part in str(spec).split('|'):
            if spec_part == 'original':
                result.append((Filter.OPERATION_NAMES['original'], None))
                continue

            match = re.match(r'(width|height)-(\d+)$', spec_part)
            if match:
                result.append((Filter.OPERATION_NAMES[match.group(1)],
                               int(match.group(2))))
                continue

            match = re.match(r'(max|min|fill)-(\d+)x(\d+)$', spec_part)
            if match:
                width = int(match.group(2))
                height = int(match.group(3))
                result.append((Filter.OPERATION_NAMES[match.group(1)],
                               (width, height)))
                continue

            match = re.match(r'(crop)-(\d+),(\d+):(\d+),(\d+)$', spec_part)
            if match:
                left = int(match.group(2))
                top = int(match.group(3))
                right = int(match.group(4))
                bottom = int(match.group(5))
                result.append((Filter.OPERATION_NAMES[match.group(1)],
                               (left, top, right, bottom)))
                continue

            match = re.match(r'(forcewidth|forceheight)-(\d+)$', spec_part)
            if match:
                result.append((Filter.OPERATION_NAMES[match.group(1)],
                               int(match.group(2))))
                continue

            match = re.match(r'(forcefit)-(\d+)x(\d+)$', spec_part)
            if match:
                width = int(match.group(2))
                height = int(match.group(3))
                result.append((Filter.OPERATION_NAMES[match.group(1)],
                               (width, height)))
                continue

            # Spec is not one of our recognised patterns
            raise Filter.InvalidFilterSpecError("Invalid image filter spec: %r"
                                                % spec_part)

        return result


    @cached_property
    def _method(self):
        return self._parse_spec_string()

    def is_valid(self):
        try:
            self._parse_spec_string()
            return True
        except Filter.InvalidFilterSpecError:
            return False

    def process_image(self, input_file, output_file=None, focal_point=None, backend_name='default'):
        """
        Run this filter on the given image file then write the result into output_file and return it
        If output_file is not given, a new BytesIO will be used instead
        """
        # Get backend
        backend = get_image_backend(backend_name)

        spec_pipeline = self._parse_spec_string()

        # Open image
        input_file.open('rb')
        image = backend.open_image(input_file)
        file_format = image.format

        # execute each of the transformations in the pipeline in sequence
        for method_name, method_arg in spec_pipeline:
            method = getattr(backend, method_name)
            image = method(image, method_arg)

        # Make sure we have an output file
        if output_file is None:
            output_file = BytesIO()

        # Write output
        backend.save_image(image, output_file, file_format)

        # Close the input file
        input_file.close()

        return output_file


class AbstractRendition(models.Model):
    filter = models.ForeignKey('Filter', related_name='+')
    file = models.ImageField(upload_to='images', width_field='width', height_field='height')
    width = models.IntegerField(editable=False)
    height = models.IntegerField(editable=False)
    focal_point_key = models.CharField(max_length=255, default='', null=False,
                                       blank=True, editable=False)

    @property
    def url(self):
        return self.file.url

    @property
    def attrs(self):
        return mark_safe(
            'src="%s" width="%d" height="%d" alt="%s"' % (
                escape(self.url), self.width, self.height,
                escape(self.image.title))
        )

    def img_tag(self, extra_attributes=None):
        if extra_attributes:
            extra_attributes_string = format_html_join(' ', '{0}="{1}"', extra_attributes.items())
            return mark_safe('<img %s %s>' % (self.attrs, extra_attributes_string))
        else:
            return mark_safe('<img %s>' % self.attrs)

    class Meta:
        abstract = True


class Rendition(AbstractRendition):
    image = models.ForeignKey('Image', related_name='renditions')

    class Meta:
        unique_together = (
            ('image', 'filter', 'focal_point_key'),
        )


class UserRendition(AbstractRendition):
    image = models.ForeignKey('Image', related_name='user_renditions')

    class Meta:
        unique_together = (
            ('image', 'filter', 'focal_point_key'),
        )

    def get_rendition(self, filter):
        # we need to construct a new filter combining what we've been passed and
        # the filter used to get THIS rendition
        if not hasattr(filter, 'process_image'):
            filter = '|'.join([self.filter.spec, filter])
        else:
            filter = '|'.join([self.filter.spec, filter.spec])

        filter, created = Filter.objects.get_or_create(spec=filter)

        try:
            rendition = self.image.renditions.get(filter=filter)
        except ObjectDoesNotExist:
            file_field = self.image.file

            # If we have a backend attribute then pass it to process
            # image - else pass 'default'
            backend_name = getattr(self, 'backend', 'default')

            try:
                # CDN drivers are buggy and fail to raise proper exceptions
                # on absence of files.
                if not file_field.storage.exists(file_field.file.name):
                    raise IOError('file not found')

                generated_image = filter.process_image(file_field.file,
                                                   backend_name=backend_name)

                output_filename = _generate_output_filename(
                                        file_field.file.name, filter.spec)

                generated_image_file = File(generated_image,
                                            name=output_filename)
            except IOError:
                return _rendition_for_missing_image(type(self), self.image)

            rendition, created = self.image.renditions.get_or_create(
                filter=filter, defaults={'file': generated_image_file})

        return rendition


# Receive the pre_delete signal and delete the file associated with the model instance.
@receiver(pre_delete, sender=Rendition)
def rendition_delete(sender, instance, **kwargs):
    # Pass false so FileField doesn't save the model.
    instance.file.delete(False)


# Receive the pre_delete signal and delete the file associated with the model instance.
@receiver(pre_delete, sender=UserRendition)
def user_rendition_delete(sender, instance, **kwargs):
    # Pass false so FileField doesn't save the model.
    instance.file.delete(False)
