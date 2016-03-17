from __future__ import unicode_literals

import os.path
import hashlib
from contextlib import contextmanager
from collections import OrderedDict

from taggit.managers import TaggableManager
from willow.image import Image as WillowImage

import django
from django.core.files import File
from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.signals import pre_delete, pre_save
from django.dispatch.dispatcher import receiver
from django.utils.safestring import mark_safe
from django.utils.six import BytesIO, text_type
from django.forms.widgets import flatatt
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.six import string_types
from django.core.urlresolvers import reverse

from unidecode import unidecode

from wagtail.wagtailcore import hooks
from wagtail.wagtailcore.models import CollectionMember
from wagtail.wagtailadmin.taggable import TagSearchable
from wagtail.wagtailsearch import index
from wagtail.wagtailsearch.queryset import SearchableQuerySetMixin
from wagtail.wagtailimages.rect import Rect
from wagtail.wagtailimages.exceptions import InvalidFilterSpecError
from wagtail.wagtailadmin.utils import get_object_usage


# A mapping of image formats to extensions
FORMAT_EXTENSIONS = {
    'jpeg': 'jpg',
    'png': 'png',
    'gif': 'gif',
}


class SourceImageIOError(IOError):
    """
    Custom exception to distinguish IOErrors that were thrown while opening the source image
    """
    pass


def _generate_output_filename(input_filename, output_format,
                              spec_hash,
                              max_len=80):
    input_filename_parts = os.path.basename(input_filename).split('.')
    filename_without_extension = '.'.join(input_filename_parts[:-1])
    filename_extension = FORMAT_EXTENSIONS[output_format]

    # we want to condense arbitrarily long specs into a finite string
    #
    extra_name_length = (len(spec_hash) + len(filename_extension)
                            + 2) # + 2 for the '.' used

    if extra_name_length >= max_len:
        raise RuntimeError('image file path is too long: {}'.format(
                                                                input_filename))

    # trim filename base so that we're well under 100 chars
    filename_without_extension = filename_without_extension[:max_len - extra_name_length]
    output_filename_parts = [filename_without_extension,
                             spec_hash, filename_extension]

    output_filename = '.'.join(output_filename_parts)
    return output_filename


def _rendition_for_missing_image(rendition_cls, image, filter):
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
    rendition.file.name = 'source-image-not-found'
    rendition.filter = filter
    return rendition


def get_upload_to(instance, filename):
    # Dumb proxy to instance method.
    return instance.get_upload_to(filename)


class ImageQuerySet(SearchableQuerySetMixin, models.QuerySet):
    pass


class WillowImageWrapper(object):
    def is_stored_locally(self):
        """
        Returns True if the image is hosted on the local filesystem
        """
        try:
            self.file.path

            return True
        except NotImplementedError:
            return False

    @contextmanager
    def get_willow_image(self):
        # Open file if it is closed
        close_file = False
        try:
            image_file = self.file

            if self.file.closed:
                # Reopen the file
                if self.is_stored_locally():
                    self.file.open('rb')
                else:
                    # Some external storage backends don't allow reopening
                    # the file. Get a fresh file instance. #1397
                    storage = self._meta.get_field('file').storage
                    image_file = storage.open(self.file.name, 'rb')

                close_file = True
        except IOError as e:
            # re-throw this as a SourceImageIOError so that calling code can distinguish
            # these from IOErrors elsewhere in the process
            raise SourceImageIOError(text_type(e))

        # Seek to beginning
        image_file.seek(0)

        try:
            yield WillowImage.open(image_file)
        finally:
            if close_file:
                image_file.close()


@python_2_unicode_compatible
class AbstractImage(CollectionMember, TagSearchable, WillowImageWrapper):
    title = models.CharField(max_length=255, verbose_name=_('title'))
    file = models.ImageField(
        verbose_name=_('file'), upload_to=get_upload_to, width_field='width', height_field='height'
    )
    width = models.IntegerField(verbose_name=_('width'), editable=False)
    height = models.IntegerField(verbose_name=_('height'), editable=False)
    created_at = models.DateTimeField(verbose_name=_('created at'), auto_now_add=True, db_index=True)
    uploaded_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_('uploaded by user'),
        null=True, blank=True, editable=False, on_delete=models.SET_NULL
    )
    show_in_catalogue = models.BooleanField(default=True)

    tags = TaggableManager(blank=True, verbose_name=_('tags'),
            help_text=_('To enter multi-word tags, use double quotes: "some tag".'))

    focal_point_x = models.PositiveIntegerField(null=True, blank=True)
    focal_point_y = models.PositiveIntegerField(null=True, blank=True)
    focal_point_width = models.PositiveIntegerField(null=True, blank=True)
    focal_point_height = models.PositiveIntegerField(null=True, blank=True)

    file_size = models.PositiveIntegerField(null=True, editable=False)

    objects = ImageQuerySet.as_manager()

    def get_file_size(self):
        if self.file_size is None:
            try:
                self.file_size = self.file.size
            except OSError:
                # File doesn't exist
                return

            self.save(update_fields=['file_size'])

        return self.file_size

    def get_upload_to(self, filename):
        folder_name = 'original_images'
        filename = self.file.field.storage.get_valid_name(filename)

        # do a unidecode in the filename and then
        # replace non-ascii characters in filename with _ , to sidestep issues with filesystem encoding
        filename = "".join((i if ord(i) < 128 else '_') for i in unidecode(filename))

        # Truncate filename so it fits in the 100 character limit
        # https://code.djangoproject.com/ticket/9893
        while len(os.path.join(folder_name, filename)) >= 95:
            prefix, dot, extension = filename.rpartition('.')
            filename = prefix[:-1] + dot + extension
        return os.path.join(folder_name, filename)

    def get_usage(self):
        return get_object_usage(self)

    @property
    def usage_url(self):
        return reverse('wagtailimages:image_usage',
                       args=(self.id,))

    search_fields = TagSearchable.search_fields + CollectionMember.search_fields + (
        index.FilterField('uploaded_by_user'),
        index.FilterField('show_in_catalogue'),
    )

    def __str__(self):
        return self.title

    def get_rect(self):
        return Rect(0, 0, self.width, self.height)

    def get_focal_point(self):
        if self.focal_point_x is not None and \
           self.focal_point_y is not None and \
           self.focal_point_width is not None and \
           self.focal_point_height is not None:
            return Rect.from_point(
                self.focal_point_x,
                self.focal_point_y,
                self.focal_point_width,
                self.focal_point_height,
            )

    def has_focal_point(self):
        return self.get_focal_point() is not None

    def set_focal_point(self, rect):
        if rect is not None:
            self.focal_point_x = rect.centroid_x
            self.focal_point_y = rect.centroid_y
            self.focal_point_width = rect.width
            self.focal_point_height = rect.height
        else:
            self.focal_point_x = None
            self.focal_point_y = None
            self.focal_point_width = None
            self.focal_point_height = None

    def get_suggested_focal_point(self):
        with self.get_willow_image() as willow:
            faces = willow.detect_faces()

            if faces:
                # Create a bounding box around all faces
                left = min(face[0] for face in faces)
                top = min(face[1] for face in faces)
                right = max(face[2] for face in faces)
                bottom = max(face[3] for face in faces)
                focal_point = Rect(left, top, right, bottom)
            else:
                features = willow.detect_features()
                if features:
                    # Create a bounding box around all features
                    left = min(feature[0] for feature in features)
                    top = min(feature[1] for feature in features)
                    right = max(feature[0] for feature in features)
                    bottom = max(feature[1] for feature in features)
                    focal_point = Rect(left, top, right, bottom)
                else:
                    return None

        # Add 20% to width and height and give it a minimum size
        x, y = focal_point.centroid
        width, height = focal_point.size

        width *= 1.20
        height *= 1.20

        width = max(width, 100)
        height = max(height, 100)

        return Rect.from_point(x, y, width, height)

    @classmethod
    def get_rendition_model(cls):
        """ Get the Rendition model for this Image model """
        if django.VERSION >= (1, 9):
            return cls.renditions.rel.related_model
        else:
            return cls.renditions.related.related_model

    def _get_rendition(self, renditions, filter, focal_point_key=''):
        if isinstance(filter, string_types):
            filter, created = Filter.objects.get_or_create(spec=filter)

        spec_hash = filter.get_cache_key(self)

        try:
            rendition = renditions.get(
                filter=filter,
                focal_point_key=focal_point_key,
            )
        except ObjectDoesNotExist:
            try:
                # Generate the rendition image
                generated_image = filter.run(self, BytesIO())
            except IOError:
                return _rendition_for_missing_image(renditions.model, self,
                                                    filter=filter)

            # Generate filename
            input_filename = os.path.basename(self.file.name)
            output_filename = _generate_output_filename(
                                input_filename,
                                generated_image.format_name,
                                spec_hash)

            rendition, created = renditions.get_or_create(
                filter=filter,
                focal_point_key=focal_point_key,
                defaults={'file': File(generated_image.f, name=output_filename)}
            )

        return rendition

    def get_rendition(self, filter):
        return self._get_rendition(self.renditions, filter,
                                   self.get_focal_point_key())

    def get_user_rendition(self, filter):
        return self._get_rendition(self.user_renditions, filter)

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
        from wagtail.wagtailimages.permissions import permission_policy
        return permission_policy.user_has_permission_for_instance(user, 'change', self)

    def get_focal_point_key(self):
        # generate new filename derived from old one, inserting the filter spec and focal point key before the extension
        if self.has_focal_point():
            return self.get_focal_point().get_key()
        else:
            return ''

    class Meta:
        abstract = True


class Image(AbstractImage):
    admin_form_fields = (
        'title',
        'file',
        'collection',
        'tags',
        'focal_point_x',
        'focal_point_y',
        'focal_point_width',
        'focal_point_height',
    )


# Do smartcropping calculations when user saves an image without a focal point
@receiver(pre_save, sender=Image)
def image_feature_detection(sender, instance, **kwargs):
    if getattr(settings, 'WAGTAILIMAGES_FEATURE_DETECTION_ENABLED', False):
        # Make sure the image doesn't already have a focal point
        if not instance.has_focal_point():
            # Set the focal point
            instance.set_focal_point(instance.get_suggested_focal_point())


# Receive the pre_delete signal and delete the file associated with the model instance.
@receiver(pre_delete, sender=Image)
def image_delete(sender, instance, **kwargs):
    # Pass false so FileField doesn't save the model.
    instance.file.delete(False)


def get_image_model():
    from django.conf import settings
    from django.apps import apps

    try:
        app_label, model_name = settings.WAGTAILIMAGES_IMAGE_MODEL.split('.')
    except AttributeError:
        return Image
    except ValueError:
        raise ImproperlyConfigured("WAGTAILIMAGES_IMAGE_MODEL must be of the form 'app_label.model_name'")

    image_model = apps.get_model(app_label, model_name)
    if image_model is None:
        raise ImproperlyConfigured(
            "WAGTAILIMAGES_IMAGE_MODEL refers to model '%s' that has not been installed" %
            settings.WAGTAILIMAGES_IMAGE_MODEL
        )
    return image_model


class Filter(models.Model):
    """
    Represents one or more operations that can be applied to an Image to produce a rendition
    appropriate for final display on the website. Usually this would be a resize operation,
    but could potentially involve colour processing, etc.
    """

    # The spec pattern is operation1-var1-var2|operation2-var1
    spec = models.CharField(max_length=255, unique=True)

    @cached_property
    def operations(self):
        # Search for operations
        self._search_for_operations()

        # Build list of operation objects
        operations = []
        for op_spec in self.spec.split('|'):
            op_spec_parts = op_spec.split('-')

            if op_spec_parts[0] not in self._registered_operations:
                raise InvalidFilterSpecError("Unrecognised operation: %s" % op_spec_parts[0])

            op_class = self._registered_operations[op_spec_parts[0]]
            operations.append(op_class(*op_spec_parts))
        return operations

    def run(self, image, output):
        with image.get_willow_image() as willow:
            original_format = willow.format_name

            # Fix orientation of image
            willow = willow.auto_orient()

            for operation in self.operations:
                willow = operation.run(willow, image) or willow

            if original_format == 'jpeg':
                # Allow changing of JPEG compression quality
                if hasattr(settings, 'WAGTAILIMAGES_JPEG_QUALITY'):
                    quality = settings.WAGTAILIMAGES_JPEG_QUALITY
                else:
                    quality = 85

                return willow.save_as_jpeg(output, quality=quality)
            elif original_format == 'gif':
                # Convert image to PNG if it's not animated
                if not willow.has_animation():
                    return willow.save_as_png(output)
                else:
                    return willow.save_as_gif(output)
            elif original_format == 'bmp':
                # Convert to PNG
                return willow.save_as_png(output)
            else:
                return willow.save(original_format, output)

    def get_cache_key(self, image):
        return hashlib.sha1(self.spec).hexdigest()[:8] + self.get_vary_key(image)


    def get_vary_key(self, image):
        vary_parts = []

        for operation in self.operations:
            for field in getattr(operation, 'vary_fields', []):
                value = getattr(image, field, '')
                vary_parts.append(str(value))

        vary_string = '-'.join(vary_parts)

        # Return blank string if there are no vary fields
        if not vary_string:
            return ''

        return hashlib.sha1(vary_string.encode('utf-8')).hexdigest()[:8]

    _registered_operations = None

    @classmethod
    def _search_for_operations(cls):
        if cls._registered_operations is not None:
            return

        operations = []
        for fn in hooks.get_hooks('register_image_operations'):
            operations.extend(fn())

        cls._registered_operations = dict(operations)


class AbstractRendition(models.Model):
    filter = models.ForeignKey(Filter, related_name='+')
    file = models.ImageField(upload_to='images', width_field='width', height_field='height')
    width = models.IntegerField(editable=False)
    height = models.IntegerField(editable=False)
    focal_point_key = models.CharField(max_length=255, blank=True, default='', editable=False)

    @property
    def url(self):
        return self.file.url

    @property
    def alt(self):
        return self.image.title

    @property
    def attrs(self):
        """
        The src, width, height, and alt attributes for an <img> tag, as a HTML
        string
        """
        return flatatt(self.attrs_dict)

    @property
    def attrs_dict(self):
        """
        A dict of the src, width, height, and alt attributes for an <img> tag.
        """
        return OrderedDict([
            ('src', self.url),
            ('width', self.width),
            ('height', self.height),
            ('alt', self.alt),
        ])

    def img_tag(self, extra_attributes={}):
        attrs = self.attrs_dict.copy()
        attrs.update(extra_attributes)
        return mark_safe('<img{}>'.format(flatatt(attrs)))

    def __html__(self):
        return self.img_tag()

    class Meta:
        abstract = True


class Rendition(AbstractRendition):
    image = models.ForeignKey(Image, related_name='renditions')

    class Meta:
        unique_together = (
            ('image', 'filter', 'focal_point_key'),
        )


class UserRendition(AbstractRendition, WillowImageWrapper):
    image = models.ForeignKey('Image', related_name='user_renditions')

    class Meta:
        unique_together = (
            ('image', 'filter', 'focal_point_key'),
        )

    def get_rendition(self, filter):
        # we need to construct a new filter combining what we've been passed
        # and the filter used to get THIS rendition
        if not hasattr(filter, 'run'):
            filter = '|'.join([self.filter.spec, filter])
        else:
            filter = '|'.join([self.filter.spec, filter.spec])

        filter, created = Filter.objects.get_or_create(spec=filter)

        spec_hash = filter.get_cache_key(self)

        try:
            rendition = self.image.renditions.get(
                filter=filter,
            )
        except ObjectDoesNotExist:
            try:
                # Generate the rendition image
                generated_image = filter.run(self, BytesIO())
            except IOError:
                return _rendition_for_missing_image(
                            self.image.renditions.model,
                            self.image, filter=filter)

            # Generate filename
            input_filename = os.path.basename(self.file.name)

            output_filename = _generate_output_filename(
                input_filename, generated_image.format_name,
                spec_hash)

            rendition, created = self.image.renditions.get_or_create(
                filter=filter,
                defaults={'file': File(generated_image.f,
                                       name=output_filename)}
            )

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
