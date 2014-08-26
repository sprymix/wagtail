from django.conf.urls import url
from wagtail.wagtaildocs.views import documents, chooser, multiple


urlpatterns = [
    url(r'^$', documents.index, name='wagtaildocs_index'),
    url(r'^add/$', documents.add, name='wagtaildocs_add_document'),
    url(r'^edit/(\d+)/$', documents.edit, name='wagtaildocs_edit_document'),
    url(r'^delete/(\d+)/$', documents.delete,
        name='wagtaildocs_delete_document'),

    url(r'^multiple/add/$', multiple.add, name='wagtaildocs_add_multiple'),
    url(r'^multiple/(\d+)/$', multiple.edit,
        name='wagtaildocs_edit_multiple'),
    url(r'^multiple/(\d+)/delete/$', multiple.delete,
        name='wagtaildocs_delete_multiple'),

    url(r'^chooser/$', chooser.chooser, name='wagtaildocs_chooser'),
    url(r'^chooser/(\d+)/$', chooser.document_chosen,
        name='wagtaildocs_document_chosen'),
    url(r'^chooser/upload/$', chooser.chooser_upload,
        name='wagtaildocs_chooser_upload'),
    url(r'^chooser/(\d+)/select/$', chooser.chooser_select,
        name='wagtaildocs_chooser_select'),

    url(r'^usage/(\d+)/$', documents.usage, name='wagtaildocs_document_usage'),
]
