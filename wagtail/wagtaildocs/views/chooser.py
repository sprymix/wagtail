from __future__ import absolute_import, unicode_literals

import json
import uuid

from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse, HttpResponseBadRequest
from django.template.loader import render_to_string

from wagtail.utils.pagination import paginate
from wagtail.wagtailadmin.forms import SearchForm
from wagtail.wagtailadmin.modal_workflow import render_modal_workflow
from wagtail.wagtailadmin.utils import PermissionPolicyChecker
from wagtail.wagtailcore.models import Collection
from wagtail.wagtaildocs.forms import get_document_form
from wagtail.wagtaildocs.forms import get_document_multi_form
from wagtail.wagtaildocs.models import get_document_model
from wagtail.wagtaildocs.permissions import permission_policy
from wagtail.wagtailsearch import index as search_index

permission_checker = PermissionPolicyChecker(permission_policy)


def get_document_json(document):
    """
    helper function: given a document, return the json to pass back to the
    chooser panel
    """

    return json.dumps({
        'id': document.id,
        'title': document.title,
        'url': document.url,
        'edit_link': reverse('wagtaildocs:edit', args=(document.id,)),
    })


def chooser(request):
    Document = get_document_model()

    if permission_policy.user_has_permission(request.user, 'add'):
        DocumentForm = get_document_form(Document)
        uploadform = DocumentForm(user=request.user)
    else:
        uploadform = None

    documents = []

    q = None
    is_searching = False
    if 'q' in request.GET or 'p' in request.GET or 'collection_id' in request.GET:
        documents = Document.objects.all()

        collection_id = request.GET.get('collection_id')
        if collection_id:
            documents = documents.filter(collection=collection_id)

        searchform = SearchForm(request.GET)
        if searchform.is_valid():
            q = searchform.cleaned_data['q']

            documents = documents.search(q)
            is_searching = True
        else:
            documents = documents.order_by('-created_at')
            is_searching = False

        # Pagination
        paginator, documents = paginate(request, documents, per_page=10)

        return render(request, "wagtaildocs/chooser/results.html", {
            'documents': documents,
            'query_string': q,
            'is_searching': is_searching,
        })
    else:
        searchform = SearchForm()

        collections = Collection.objects.all()
        if len(collections) < 2:
            collections = None

        documents = Document.objects.order_by('-created_at')
        paginator, documents = paginate(request, documents, per_page=10)

    return render_modal_workflow(request, 'wagtaildocs/chooser/chooser.html', 'wagtaildocs/chooser/chooser.js', {
        'documents': documents,
        'uploadform': uploadform,
        'searchform': searchform,
        'collections': collections,
        'is_searching': False,
        'uploadid': uuid.uuid4(),
    })


def document_chosen(request, document_id):
    doc = get_object_or_404(get_document_model(), id=document_id)
    Document = get_document_model()
    DocumentMultiForm = get_document_multi_form(Document)

    # handle some updated data if this is a POST
    if request.POST:
        if not request.is_ajax():
            return HttpResponseBadRequest("Cannot POST to this view without AJAX")

        form = DocumentMultiForm(
            request.POST, request.FILES, instance=doc, prefix='doc-' + document_id, user=request.user
        )

        if form.is_valid():
            form.save()

        # Reindex the doc to make sure all tags are indexed
        search_index.insert_or_update_object(doc)

    return render_modal_workflow(
        request, None, 'wagtaildocs/chooser/document_chosen.js',
        {'document_json': get_document_json(doc)}
    )


@permission_checker.require('add')
def chooser_upload(request):
    Document = get_document_model()
    DocumentForm = get_document_form(Document)
    DocumentMultiForm = get_document_multi_form(Document)

    if request.method == 'POST':
        if not request.is_ajax():
            return HttpResponseBadRequest("Cannot POST to this view without AJAX")

        if not request.FILES:
            return HttpResponseBadRequest("Must upload a file")

        # Save it
        document = Document(uploaded_by_user=request.user, title=request.FILES['files[]'].name, file=request.FILES['files[]'])
        document.save()

        # Success! Send back an edit form for this image to the user
        form = DocumentMultiForm(instance=document, prefix='doc-%d' % document.id, user=request.user)

        return JsonResponse({
            'success': True,
            'doc_id': int(document.id),
            'form': render_to_string('wagtaildocs/chooser/update.html', {
                'doc': document,
                'form': form,
            }, request=request),
        })
    else:
        form = DocumentForm(user=request.user)

    documents = Document.objects.order_by('title')

    return render_modal_workflow(
        request, 'wagtaildocs/chooser/chooser.html', 'wagtaildocs/chooser/chooser.js',
        {'documents': documents, 'uploadform': form}
    )
