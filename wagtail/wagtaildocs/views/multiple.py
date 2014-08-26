import json

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import permission_required
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied, ValidationError
from django.views.decorators.vary import vary_on_headers
from django.http import HttpResponse, HttpResponseBadRequest
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _

from wagtail.wagtaildocs.models import Document
from wagtail.wagtaildocs.forms import DocumentForm, DocumentFormMulti
from wagtail.wagtailadmin.forms import SearchForm


def json_response(document):
    return HttpResponse(json.dumps(document), content_type='application/json')


@permission_required('wagtaildocs.add_document')
@vary_on_headers('X-Requested-With')
def add(request):
    if request.method == 'POST':
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
        form = DocumentForm(instance=doc, prefix='doc-%d' % doc.id)

        return json_response({
            'success': True,
            'doc_id': int(doc.id),
            'form': render_to_string('wagtaildocs/multiple/edit_form.html', {
                'doc': doc,
                'form': form,
            }, context_instance=RequestContext(request)),
        })

    return render(request, 'wagtaildocs/multiple/add.html', {})


@require_POST
@permission_required('wagtailadmin.access_admin')  # more specific permission tests are applied within the view
def edit(request, doc_id, callback=None):
    doc = get_object_or_404(Document, id=doc_id)

    if not request.is_ajax():
        return HttpResponseBadRequest("Cannot POST to this view without AJAX")

    if not doc.is_editable_by_user(request.user):
        raise PermissionDenied

    form = DocumentFormMulti(request.POST, request.FILES, instance=doc,
                             prefix='doc-' + doc_id)

    if form.is_valid():
        form.save()
        return json_response({
            'success': True,
            'doc_id': int(doc_id),
        })
    else:
        return json_response({
            'success': False,
            'doc_id': int(doc_id),
            'form': render_to_string('wagtaildocs/multiple/edit_form.html', {
                'doc': doc,
                'form': form,
            }, context_instance=RequestContext(request)),
        })


@require_POST
@permission_required('wagtailadmin.access_admin')  # more specific permission tests are applied within the view
def delete(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)

    if not request.is_ajax():
        return HttpResponseBadRequest("Cannot POST to this view without AJAX")

    if not doc.is_editable_by_user(request.user):
        raise PermissionDenied

    doc.delete()

    return json_response({
        'success': True,
        'doc_id': int(doc_id),
    })
