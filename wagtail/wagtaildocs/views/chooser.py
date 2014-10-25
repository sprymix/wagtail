import json
import uuid

from django.shortcuts import get_object_or_404, render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from wagtail.wagtailadmin.modal_workflow import render_modal_workflow
from wagtail.wagtailadmin.forms import SearchForm

from wagtail.wagtaildocs.models import Document
from wagtail.wagtaildocs.forms import DocumentForm, DocumentFormMulti


@permission_required('wagtailadmin.access_admin')
def chooser(request):
    if request.user.has_perm('wagtaildocs.add_document'):
        uploadform = DocumentForm()
    else:
        uploadform = None

    documents = []

    q = None
    is_searching = False
    if 'q' in request.GET or 'p' in request.GET:
        searchform = SearchForm(request.GET)
        if searchform.is_valid():
            q = searchform.cleaned_data['q']

            # page number
            p = request.GET.get("p", 1)

            documents = Document.search(q, results_per_page=10, prefetch_tags=True)

            is_searching = True

        else:
            documents = Document.objects.order_by('-created_at')

            p = request.GET.get("p", 1)
            paginator = Paginator(documents, 10)

            try:
                documents = paginator.page(p)
            except PageNotAnInteger:
                documents = paginator.page(1)
            except EmptyPage:
                documents = paginator.page(paginator.num_pages)

            is_searching = False

        return render(request, "wagtaildocs/chooser/results.html", {
            'documents': documents,
            'query_string': q,
            'is_searching': is_searching,
        })
    else:
        searchform = SearchForm()

        documents = Document.objects.order_by('-created_at')
        p = request.GET.get("p", 1)
        paginator = Paginator(documents, 10)

        try:
            documents = paginator.page(p)
        except PageNotAnInteger:
            documents = paginator.page(1)
        except EmptyPage:
            documents = paginator.page(paginator.num_pages)

    return render_modal_workflow(request, 'wagtaildocs/chooser/chooser.html', 'wagtaildocs/chooser/chooser.js', {
        'documents': documents,
        'uploadform': uploadform,
        'searchform': searchform,
        'is_searching': False,
        'uploadid': uuid.uuid4(),
    })


@permission_required('wagtailadmin.access_admin')
def document_chosen(request, document_id):
    document = get_object_or_404(Document, id=document_id)

    document_json = json.dumps({
        'id': document.id,
        'title': document.title,
        'url': document.url
    })

    return render_modal_workflow(
        request, None, 'wagtaildocs/chooser/document_chosen.js',
        {'document_json': document_json}
    )


def json_response(document):
    return HttpResponse(json.dumps(document), content_type='application/json')


@require_POST
@permission_required('wagtaildocs.add_document')
def chooser_upload(request):
    if not request.is_ajax():
        return HttpResponseBadRequest("Cannot POST to this view without AJAX")

    if not request.FILES:
        return HttpResponseBadRequest("Must upload a file")

    # Save it
    doc = Document(uploaded_by_user=request.user,
                   title=request.FILES['files[]'].name,
                   file=request.FILES['files[]'])
    doc.save()

    # Success! Send back an edit form for this doc to the user
    form = DocumentFormMulti(instance=doc, prefix='doc-%d' % doc.id)

    return json_response({
        'success': True,
        'doc_id': int(doc.id),
        'form': render_to_string('wagtaildocs/chooser/update.html', {
            'doc': doc,
            'form': form,
        }, context_instance=RequestContext(request)),
    })


@require_POST
@permission_required('wagtailadmin.access_admin')
def chooser_select(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)

    if not request.is_ajax():
        return HttpResponseBadRequest("Cannot POST to this view without AJAX")

    if not document.is_editable_by_user(request.user):
        raise PermissionDenied

    form = DocumentFormMulti(request.POST, request.FILES, instance=document,
                             prefix='doc-' + doc_id)

    if form.is_valid():
        form.save()
        document_json = json.dumps({
            'id': document.id,
            'title': document.title,
            'url': document.url
        })
        return render_modal_workflow(
            request, None, 'wagtaildocs/chooser/document_chosen.js',
            {'document_json': document_json}
        )
