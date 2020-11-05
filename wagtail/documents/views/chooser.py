import json
import uuid

from django import http
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import ugettext as _

from wagtail.admin.auth import PermissionPolicyChecker
from wagtail.admin.forms.search import SearchForm
from wagtail.admin.modal_workflow import render_modal_workflow
from wagtail.core import hooks
from wagtail.core.models import Collection
from wagtail.core.utils import filename_to_human_readable
from wagtail.documents import get_document_model
from wagtail.documents.forms import get_document_form
from wagtail.documents.permissions import permission_policy
from wagtail.search import index as search_index

from ..forms import get_document_multi_form


permission_checker = PermissionPolicyChecker(permission_policy)


def get_chooser_context():
    """construct context variables needed by the chooser JS"""
    return {
        'step': 'chooser',
        'error_label': _("Server Error"),
        'error_message': _("Report this error to your webmaster with the following information:"),
        'tag_autocomplete_url': reverse('wagtailadmin_tag_autocomplete'),
    }


def get_document_result_data(document):
    """
    helper function: given a document, return the json data to pass back to the
    chooser panel
    """

    return {
        'id': document.id,
        'title': document.title,
        'url': document.url,
        'filename': document.filename,
        'edit_link': reverse('wagtaildocs:edit', args=(document.id,)),
    }


def chooser(request):
    Document = get_document_model()

    if permission_policy.user_has_permission(request.user, 'add'):
        DocumentForm = get_document_form(Document)
        uploadform = DocumentForm(user=request.user, prefix='document-chooser-upload')
    else:
        uploadform = None

    documents = Document.objects.all()

    # allow hooks to modify the queryset
    for hook in hooks.get_hooks('construct_document_chooser_queryset'):
        documents = hook(documents, request)

    q = None
    if 'q' in request.GET or 'p' in request.GET or 'collection_id' in request.GET:

        collection_id = request.GET.get('collection_id')
        if collection_id:
            documents = documents.filter(collection=collection_id)
        documents_exist = documents.exists()

        searchform = SearchForm(request.GET)
        if searchform.is_valid():
            q = searchform.cleaned_data['q']

            documents = documents.search(q)
            is_searching = True
        else:
            documents = documents.order_by('-created_at')
            is_searching = False

        # Pagination
        paginator = Paginator(documents, per_page=10)
        documents = paginator.get_page(request.GET.get('p'))

        return render(request, "wagtaildocs/chooser/results.html", {
            'documents': documents,
            'documents_exist': documents_exist,
            'uploadform': uploadform,
            'query_string': q,
            'is_searching': is_searching,
            'collection_id': collection_id,
        })
    else:
        searchform = SearchForm()

        collections = Collection.objects.all()
        if len(collections) < 2:
            collections = None
        else:
            collections = Collection.order_for_display(collections)

        documents = documents.order_by('-created_at')
        documents_exist = documents.exists()
        paginator = Paginator(documents, per_page=10)
        documents = paginator.get_page(request.GET.get('p'))

        return render_modal_workflow(request, 'wagtaildocs/chooser/chooser.html', None, {
            'documents': documents,
            'documents_exist': documents_exist,
            'uploadform': uploadform,
            'searchform': searchform,
            'collections': collections,
            'is_searching': False,
            'uploadid': uuid.uuid4(),
        }, json_data=get_chooser_context())


def document_chosen(request, document_id):
    doc = get_object_or_404(get_document_model(), id=document_id)
    Document = get_document_model()
    DocumentMultiForm = get_document_multi_form(Document)

    # handle some updated data if this is a POST
    if request.POST:
        if not request.is_ajax():
            return http.HttpResponseBadRequest(
                "Cannot POST to this view without AJAX")

        form = DocumentMultiForm(
            request.POST, request.FILES, instance=doc, prefix='doc-' + document_id, user=request.user
        )

        if form.is_valid():
            form.save()

        # Reindex the doc to make sure all tags are indexed
        search_index.insert_or_update_object(doc)

    return render_modal_workflow(
        request, None, None,
        None, json_data={'step': 'document_chosen', 'result': get_document_result_data(doc)}
    )


@permission_checker.require('add')
def chooser_upload(request):
    Document = get_document_model()
    DocumentForm = get_document_form(Document)
    DocumentMultiForm = get_document_multi_form(Document)

    if request.method == 'POST':
        if not request.is_ajax():
            return http.HttpResponseBadRequest(
                "Cannot POST to this view without AJAX")

        if not request.FILES:
            return http.HttpResponseBadRequest("Must upload a file")

        # Save it
        title = filename_to_human_readable(request.FILES['files[]'].name)
        document = Document(uploaded_by_user=request.user,
                            title=title,
                            file=request.FILES['files[]'])
        document.save()

        # Success! Send back an edit form for this image to the user
        form = DocumentMultiForm(instance=document,
                                 prefix='doc-%d' % document.id,
                                 user=request.user)

        return http.JsonResponse({
            'success': True,
            'doc_id': int(document.id),
            'form': render_to_string('wagtaildocs/chooser/update.html', {
                'doc': document,
                'form': form,
            }, request=request),
        })
    else:
        form = DocumentForm(user=request.user, prefix='document-chooser-upload')

    documents = Document.objects.order_by('title')

    return render_modal_workflow(
        request, 'wagtaildocs/chooser/chooser.html', None,
        {'documents': documents, 'uploadform': form},
        json_data=get_chooser_context()
    )
