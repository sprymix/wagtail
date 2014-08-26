from django import forms
from django.forms.models import modelform_factory

from wagtail.wagtaildocs.models import Document


class DocumentForm(forms.ModelForm):
    required_css_class = "required"

    class Meta:
        model = Document
        widgets = {
            'file': forms.FileInput()
        }

class DocumentFormMulti(forms.ModelForm):
    required_css_class = "required"

    class Meta:
        model = Document
        widgets = {
            'file': forms.FileInput()
        }
        exclude = ('file',)
