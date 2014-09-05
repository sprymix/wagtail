import json
import uuid
import urllib

from django.shortcuts import get_object_or_404, render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _
from django.http import HttpResponse, HttpResponseBadRequest
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from wagtail.wagtailadmin.modal_workflow import render_modal_workflow
from wagtail.wagtailadmin.forms import SearchForm

from wagtail.wagtailimages.models import get_image_model
from wagtail.wagtailimages.forms import get_image_form, ImageInsertionForm, \
                                        ImageCropperForm, \
                                        get_image_form_for_multi
from wagtail.wagtailimages.formats import get_image_format
from wagtail.wagtailimages.utils.validators import validate_image_format


def get_image_json(image):
    """
    helper function: given an image, return the json to pass back to the
    image chooser panel
    """
    preview_image = image.get_rendition('max-130x100')

    return json.dumps({
        'id': image.id,
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
    initial = None
    crop = request.GET.get('crop')
    ratios = request.GET.get('ratios')
    default_ratio = request.GET.get('ar')
    force_selection = request.GET.get('fsel') == 'T'
    disable_selection = request.GET.get('dsel') == 'T'
    post_processing_spec = request.GET.get('pps')

    if crop:
        crop = crop.split(',')
        if len(crop) == 4:
            initial = {
                'left': crop[0],
                'top': crop[1],
                'right': crop[2],
                'bottom': crop[3],
                'force_selection': force_selection
            }
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
    for name in ('crop', 'ratios', 'ar', 'fsel', 'dsel', 'pps'):
        val = request.GET.get(name)
        if val is not None:
            params[name] = val

    return urllib.urlencode(params)


@permission_required('wagtailadmin.access_admin')
def chooser(request):
    Image = get_image_model()

    if request.user.has_perm('wagtailimages.add_image'):
        ImageForm = get_image_form()
        uploadform = ImageForm()
    else:
        uploadform = None

    will_select_format = request.GET.get('select_format')
    will_select_rendition = request.GET.get('select_rendition')

    q = None
    if 'q' in request.GET or 'p' in request.GET:
        searchform = SearchForm(request.GET)
        if searchform.is_valid():
            q = searchform.cleaned_data['q']

            # page number
            p = request.GET.get("p", 1)

            images = Image.search(q, results_per_page=12, page=p)

            is_searching = True

        else:
            images = Image.objects.order_by('-created_at')
            p = request.GET.get("p", 1)
            paginator = Paginator(images, 12)

            try:
                images = paginator.page(p)
            except PageNotAnInteger:
                images = paginator.page(1)
            except EmptyPage:
                images = paginator.page(paginator.num_pages)

            is_searching = False

        return render(request, "wagtailimages/chooser/results.html", {
            'images': images,
            'is_searching': is_searching,
            'query_string': q,
            'will_select_format': will_select_format,
            'will_select_rendition': will_select_rendition
        })
    else:
        searchform = SearchForm()

        images = Image.objects.order_by('-created_at')
        p = request.GET.get("p", 1)
        paginator = Paginator(images, 12)

        try:
            images = paginator.page(p)
        except PageNotAnInteger:
            images = paginator.page(1)
        except EmptyPage:
            images = paginator.page(paginator.num_pages)

    return render_modal_workflow(request, 'wagtailimages/chooser/chooser.html', 'wagtailimages/chooser/chooser.js', {
        'images': images,
        'uploadform': uploadform,
        'searchform': searchform,
        'is_searching': False,
        'query_string': q,
        'will_select_format': will_select_format,
        'will_select_rendition': will_select_rendition,
        'popular_tags': Image.popular_tags(),
        'uploadid': uuid.uuid4(),
        'post_processing_spec': request.GET.get('pps'),
        'additional_params': get_cropper_params(request),
    })


@permission_required('wagtailadmin.access_admin')
def image_chosen(request, image_id):
    image = get_object_or_404(get_image_model(), id=image_id)

    return render_modal_workflow(
        request, None, 'wagtailimages/chooser/image_chosen.js',
        {'image_json': get_image_json(image)}
    )


def json_response(document):
    return HttpResponse(json.dumps(document), content_type='application/json')


@require_POST
@permission_required('wagtailimages.add_image')
def chooser_upload(request):
    Image = get_image_model()
    ImageForm = get_image_form_for_multi()

    if not request.is_ajax():
        return HttpResponseBadRequest("Cannot POST to this view without AJAX")

    if not request.FILES:
        return HttpResponseBadRequest("Must upload a file")

    # Check that the uploaded file is valid
    try:
        validate_image_format(request.FILES['files[]'])
    except ValidationError as e:
        return json_response({
            'success': False,
            'error_message': '\n'.join(e.messages),
        })

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
@permission_required('wagtailimages.add_image')
def chooser_select(request, image_id):
    Image = get_image_model()
    ImageForm = get_image_form_for_multi()

    image = get_object_or_404(Image, id=image_id)

    if not request.is_ajax():
        return HttpResponseBadRequest("Cannot POST to this view without AJAX")

    if not image.is_editable_by_user(request.user):
        raise PermissionDenied

    form = ImageForm(request.POST, request.FILES, instance=image,
                     prefix='image-' + image_id)

    if form.is_valid():
        form.save()

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


@permission_required('wagtailadmin.access_admin')
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
            filter_spec = 'crop-{left},{top}:{right},{bottom}'.format(
                                                            **form.cleaned_data)
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
