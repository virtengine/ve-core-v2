from __future__ import unicode_literals

from django.conf import settings
from elasticsearch import Elasticsearch


class ElasticsearchError(Exception):
    pass


class ElasticsearchClientError(ElasticsearchError):
    pass


class ElasticsearchResultListError(ElasticsearchError):
    pass


class ElasticsearchResultList(object):

    def __init__(self, user, event_types=None):
        self.client = ElasticsearchClient()
        self.user = user
        self.event_types = event_types

    def _get_events(self, from_, size):
        return self.client.get_user_events(self.user, self.event_types, from_=from_, size=size)

    def __len__(self):
        if not hasattr(self, 'total'):
            self.total = self._get_events(0, 1)['total']
        return self.total

    def __getitem__(self, key):
        if isinstance(key, slice):
            if key.step is not None and key.step != 1:
                raise ElasticsearchResultListError('ElasticsearchResultList can be iterated only with step 1')
            events_and_total = self._get_events(key.start, key.stop - key.start)
        else:
            events_and_total = self._get_events(key, 1)
        self.total = events_and_total['total']
        return events_and_total['events']


class ElasticsearchClient(object):

    def __init__(self):
        self.client = self._get_client()

    def get_user_events(self, user, event_types=None, index='_all', from_=0, size=10):
        """
        Return events filtered for given user and total count of available for user events
        """
        body = self._get_search_body(user, event_types)
        search_results = self.client.search(index=index, body=body, from_=from_, size=size)
        return {
            'events': [r['_source'] for r in search_results['hits']['hits']],
            'total': search_results['hits']['total'],
        }

    def _get_elastisearch_settings(self):
        try:
            return settings.NODECONDUCTOR['ELASTICSEARCH']
        except (KeyError, AttributeError):
            raise ElasticsearchClientError(
                'Can not get elasticsearch settings. ELASTICSEARCH item in settings.NODECONDUCTOR has'
                'to be defined. Or enable dummy elasticsearch mode.')

    def _get_client(self):
        # TODO return dummy client here
        elasticsearch_settings = self._get_elastisearch_settings()
        path = '%(protocol)s://%(username)s:%(password)s@%(host)s:%(port)s' % elasticsearch_settings
        return Elasticsearch(
            [path],
            use_ssl=elasticsearch_settings.get('use_ssl', False),
            verify_certs=elasticsearch_settings.get('verify_certs', False),
        )

    def _get_permitted_objects_uuids(self, user):
        """
        Return list object available UUIDs for user
        """
        # XXX: this method has to be refactored, because it adds dependencies from iaas and structure apps
        from nodeconductor.structure import models as structure_models
        from nodeconductor.structure.filters import filter_queryset_for_user

        return {
            'project_uuid': filter_queryset_for_user(
                structure_models.Project.objects.all(), user).values_list('uuid', flat=True),
            'project_group_uuid': filter_queryset_for_user(
                structure_models.ProjectGroup.objects.all(), user).values_list('uuid', flat=True),
            'customer_uuid': filter_queryset_for_user(
                structure_models.Customer.objects.all(), user).values_list('uuid', flat=True),
        }

    def _format_to_elasticsearch_field_filter(self, field_name, field_values):
        """
        Return string '<field_name>:("<field_value1>", "<field_value2>"...)'
        """
        return '%s:("%s")' % (field_name, '", "'.join(field_values))

    def _get_search_body(self, user, event_types=None):
        permitted_objects_uuids = self._get_permitted_objects_uuids(user)

        query = ' OR '.join([
            self._format_to_elasticsearch_field_filter(item, uuids)
            for item, uuids in permitted_objects_uuids.items()
        ])
        if event_types:
            query = '(' + query + ') AND ' + self._format_to_elasticsearch_field_filter('event_type', event_types)

        return {"query": {"query_string": {"query": query}}}
