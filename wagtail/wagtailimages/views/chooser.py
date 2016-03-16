import json
import uuid
import urllib

from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.translation import ugettext as _
from django.http import HttpResponse, HttpResponseBadRequest
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from wagtail.utils.pagination import paginate
from wagtail.wagtailadmin.modal_workflow import render_modal_workflow
from wagtail.wagtailadmin.forms import SearchForm
from wagtail.wagtailadmin.utils import PermissionPolicyChecker
from wagtail.wagtailadmin.utils import permission_required
from wagtail.wagtailcore.models import Collection
from wagtail.wagtailsearch.backends import get_search_backends

from wagtail.wagtailimages.models import get_image_model
from wagtail.wagtailimages.forms import get_image_form, ImageInsertionForm, \
                                        ImageCropperForm
from wagtail.wagtailimages.formats import get_image_format
from wagtail.wagtailimages.permissions import permission_policy


permission_checker = PermissionPolicyChecker(permission_policy)


def get_image_json(image):
    """
    helper function: given an image, return the json to pass back to the
    image chooser panel
    """
    preview_image = image.get_rendition('max-165x165')

    return json.dumps({
        'id': image.id,
        'edit_link': reverse('wagtailimages:edit', args=(image.id,)),
        'title': image.title,
        'preview': {
            'url': preview_image.url,
            'width': preview_image.width,
            'height': preview_image.height,
        }
    })


def get_cropper_settings(request):
    '''Helper that extracts the settings for the ImageCropperForm from request
    data.'''

    # get filter spec if it was passed
    #
    initial = {}
    crop = request.GET.get('crop')
    fit = request.GET.get('fit')
    ratios = request.GET.get('ratios')
    default_ratio = request.GET.get('ar')
    force_selection = request.GET.get('fsel') == 'T'
    disable_selection = request.GET.get('dsel') == 'T'
    post_processing_spec = request.GET.get('pps')

    if crop:
        crop = crop.split(',')
        if len(crop) == 4:
            initial.update({
                'left': crop[0],
                'top': crop[1],
                'right': crop[2],
                'bottom': crop[3],
                'force_selection': force_selection
            })
    if fit:
        fit = fit.split('x')
        if len(fit) == 2:
            initial.update({
                'width': fit[0],
                'height': fit[1]
            })

    if ratios is not None:
        ratios = tuple(ratios.split(','))

    return dict(initial=initial,
                ratios=ratios,
                default_ratio=default_ratio,
                disable_selection=disable_selection,
                post_processing_spec=post_processing_spec)


def get_cropper_params(request):
    '''Helper that extracts cropper params so they can be appended to the
    URL.'''

    params = {}
    for name in ('crop', 'ratios', 'ar', 'fsel', 'dsel', 'pps', 'fit'):
        val = request.GET.get(name)
        if val is not None:
            params[name] = val

    return urllib.urlencode(params)


@permission_required('wagtailadmin.access_admin')
def chooser(request):
    Image = get_image_model()

    if permission_policy.user_has_permission(request.user, 'add'):
        ImageForm = get_image_form(Image)
        uploadform = ImageForm()
    else:
        uploadform = None

    will_select_format = request.GET.get('select_format')
    will_select_rendition = request.GET.get('select_rendition')

    images = Image.objects.order_by('-created_at') \
                          .filter(show_in_catalogue=True)

    q = None
    if (
        'q' in request.GET or 'p' in request.GET or 'tag' in request.GET or
        'collection_id' in request.GET
    ):
        # this request is triggered from search, pagination or 'popular tags';
        # we will just render the results.html fragment
        collection_id = request.GET.get('collection_id')
        if collection_id:
            images = images.filter(collection=collection_id)

        searchform = SearchForm(request.GET)
        if searchform.is_valid():
            q = searchform.cleaned_data['q']
            images = images.search(q)
            is_searching = True
        else:
            is_searching = False

            tag_name = request.GET.get('tag')
            if tag_name:
                images = images.filter(tags__name=tag_name)

        # Pagination
        paginator, images = paginate(request, images, per_page=12)

        return render(request, "wagtailimages/chooser/results.html", {
            'images': images,
            'is_searching': is_searching,
            'query_string': q,
            'will_select_format': will_select_format,
            'will_select_rendition': will_select_rendition,
            'post_processing_spec': request.GET.get('pps'),
            'additional_params': get_cropper_params(request),
        })
    else:
        searchform = SearchForm()

        collections = Collection.objects.all()
        if len(collections) < 2:
            collections = None

        paginator, images = paginate(request, images, per_page=12)

    return render_modal_workflow(request, 'wagtailimages/chooser/chooser.html', 'wagtailimages/chooser/chooser.js', {
        'images': images,
        'uploadform': uploadform,
        'searchform': searchform,
        'is_searching': False,
        'query_string': q,
        'will_select_format': will_select_format,
        'will_select_rendition': will_select_rendition,
        'popular_tags': Image.popular_tags(),
        'collections': collections,
        'uploadid': uuid.uuid4(),
        'post_processing_spec': request.GET.get('pps'),
        'additional_params': get_cropper_params(request),
    })


def image_chosen(request, image_id):
    image = get_object_or_404(get_image_model(), id=image_id)

    return render_modal_workflow(
        request, None, 'wagtailimages/chooser/image_chosen.js',
        {'image_json': get_image_json(image)}
    )


def json_response(document):
    return HttpResponse(json.dumps(document), content_type='application/json')


@require_POST
@permission_checker.require('add')
def chooser_upload(request):
    Image = get_image_model()
    ImageForm = get_image_form(Image, hide_file=True)

    if not request.is_ajax():
        return HttpResponseBadRequest("Cannot POST to this view without AJAX")

    if not request.FILES:
        return HttpResponseBadRequest("Must upload a file")

    # Save it
    image = Image(uploaded_by_user=request.user, title=request.FILES['files[]'].name, file=request.FILES['files[]'])
    image.save()

    # Success! Send back an edit form for this image to the user
    form = ImageForm(instance=image, prefix='image-%d' % image.id)

    # Keep follow-up settings
    will_select_format = request.GET.get('select_format')
    will_select_rendition = request.GET.get('select_rendition')

    return json_response({
        'success': True,
        'image_id': int(image.id),
        'form': render_to_string('wagtailimages/chooser/update.html', {
            'image': image,
            'form': form,
            'will_select_format': will_select_format,
            'will_select_rendition': will_select_rendition,
            'additional_params': get_cropper_params(request),
        }, context_instance=RequestContext(request)),
    })


@require_POST
@permission_checker.require('add')
def chooser_select(request, image_id):
    Image = get_image_model()
    ImageForm = get_image_form(hide_file=True)

    image = get_object_or_404(Image, id=image_id)

    if not request.is_ajax():
        return HttpResponseBadRequest("Cannot POST to this view without AJAX")

    if not image.is_editable_by_user(request.user):
        raise PermissionDenied

    form = ImageForm(request.POST, request.FILES, instance=image,
                     prefix='image-' + image_id)

    if form.is_valid():
        form.save()

        # Reindex the image to make sure all tags are indexed
        for backend in get_search_backends():
            backend.add(image)

        # several possibilities starting from here, based on the GET params
        #
        will_select_format = request.GET.get('select_format')
        will_select_rendition = request.GET.get('select_rendition')

        if will_select_format:
            form = ImageInsertionForm(
                            initial={'alt_text': image.default_alt_text})
            return render_modal_workflow(
                request, 'wagtailimages/chooser/select_format.html',
                'wagtailimages/chooser/select_format.js',
                {'image': image, 'form': form}
            )
        elif will_select_rendition:
            form = ImageCropperForm(**get_cropper_settings(request))
            return render_modal_workflow(
                request, 'wagtailimages/chooser/select_rendition.html',
                'wagtailimages/chooser/select_rendition.js',
                {'image': image, 'form': form}
            )
        else:
            # not specifying a format; return the image details now
            return render_modal_workflow(
                request, None, 'wagtailimages/chooser/image_chosen.js',
                {'image_json': get_image_json(image)}
            )

    else:
        # something was wrong with the submitted data
        #
        return json_response({
            'success': False,
            'image_id': int(image_id),
            'form': render_to_string('wagtailimages/chooser/update.html', {
                'image': image,
                'form': form,
                'additional_params': get_cropper_params(request),
            }, context_instance=RequestContext(request)),
        })


def chooser_select_format(request, image_id):
    image = get_object_or_404(get_image_model(), id=image_id)

    if request.POST:
        form = ImageInsertionForm(request.POST, initial={'alt_text': image.default_alt_text})
        if form.is_valid():

            format = get_image_format(form.cleaned_data['format'])
            preview_image = image.get_rendition(format.filter_spec)

            image_json = json.dumps({
                'id': image.id,
                'title': image.title,
                'format': format.name,
                'alt': form.cleaned_data['alt_text'],
                'class': format.classnames,
                'edit_link': reverse('wagtailimages:edit', args=(image.id,)),
                'preview': {
                    'url': preview_image.url,
                    'width': preview_image.width,
                    'height': preview_image.height,
                },
                'html': format.image_to_editor_html(image, form.cleaned_data['alt_text']),
            })

            return render_modal_workflow(
                request, None, 'wagtailimages/chooser/image_chosen.js',
                {'image_json': image_json}
            )
    else:
        form = ImageInsertionForm(initial={'alt_text': image.default_alt_text})

    return render_modal_workflow(
        request, 'wagtailimages/chooser/select_format.html', 'wagtailimages/chooser/select_format.js',
        {'image': image, 'form': form}
    )


@permission_required('wagtailadmin.access_admin')
def chooser_select_rendition(request, image_id):
    image = get_object_or_404(get_image_model(), id=image_id)

    if request.POST:
        form = ImageCropperForm(request.POST)

        if form.is_valid():
            # add cropping filter from the form data
            #
            filter_spec = 'crop-{left},{top}:{right},{bottom}'.format(
                                                            **form.cleaned_data)
            # add forcefit filter from the form data if needed
            #
            width = form.cleaned_data.get('width')
            height = form.cleaned_data.get('height')
            if width and height:
                filter_spec += '|forcefit-{}x{}'.format(width, height)

            post_processing_spec = request.GET.get('pps')
            if post_processing_spec:
                filter_spec = '{}|{}'.format(filter_spec, post_processing_spec)
            rendition = image.get_user_rendition(filter_spec)

        else:
            # something went wrong
            #
            raise ValidationError(_("Errors encountered while cropping."),
                                  code='invalid')

        rendition = image.get_user_rendition(filter_spec)
        preview_image = image.get_rendition(filter_spec + '|max-130x100')

        rendition_json = json.dumps({
            'id': rendition.id,
            'title': image.title,
            'original_id': image.id,
            'spec': rendition.filter.spec,
            'html': rendition.img_tag(),
            'preview': {
                'url': preview_image.url,
                'width': preview_image.width,
                'height': preview_image.height,
            },
        })
        return render_modal_workflow(
            request, None, 'wagtailimages/chooser/image_chosen.js',
            {'image_json': rendition_json}
        )

    else:
        # get filter spec if it was passed
        #
        form = ImageCropperForm(**get_cropper_settings(request))

        return render_modal_workflow(
            request, 'wagtailimages/chooser/select_rendition.html',
            'wagtailimages/chooser/select_rendition.js',
            {'image': image, 'form': form}
        )
