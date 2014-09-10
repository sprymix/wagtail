from django.db import models

from wagtail.wagtailsearch.backends.base import BaseSearch
from wagtail.wagtailsearch.indexed import Indexed


class DBSearchResults(object):
    def __init__(self, backend, queryset, return_pks=False):
        self.backend = backend
        self.queryset = queryset
        self.return_pks = return_pks

    def __getitem__(self, key):
        return self.__class__(self.backend, self.queryset.__getitem__(key),
                              return_pks=self.return_pks)

    def __iter__(self):
        if self.return_pks:
            return (instance.pk for instance in self.queryset)
        else:
            return iter(self.queryset)

    def __len__(self):
        return len(self.queryset)

    def __repr__(self):
        data = list(self[:21])
        if len(data) > 20:
            data[-1] = "...(remaining elements truncated)..."
        return repr(data)


class DBSearch(BaseSearch):
    def __init__(self, params):
        super(DBSearch, self).__init__(params)

    def reset_index(self):
        pass # Not needed

    def add_type(self, model):
        pass # Not needed

    def refresh_index(self):
        pass # Not needed

    def add(self, obj):
        pass # Not needed

    def add_bulk(self, obj_list):
        return [] # Not needed

    def delete(self, obj):
        pass # Not needed

    def _search(self, queryset, query_string, fields=None, return_pks=False):
        if query_string is not None:
            # Get fields
            if fields is None:
                fields = [field.field_name for field in queryset.model.get_searchable_search_fields()]

            # Get terms
            terms = query_string.split()
            if not terms:
                return queryset.model.objects.none()

            # Filter by terms
            for term in terms:
                term_query = models.Q()
                for field_name in fields:
                    # Check if the field exists (this will filter out indexed callables)
                    try:
                        queryset.model._meta.get_field_by_name(field_name)
                    except:
                        continue

                    # Filter on this field
                    term_query |= models.Q(**{'%s__icontains' % field_name: term})

                queryset = queryset.filter(term_query)

            # Distinct
            queryset = queryset.distinct()

        return DBSearchResults(self, queryset, return_pks=return_pks)
