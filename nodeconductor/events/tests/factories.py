from __future__ import unicode_literals

from django.core.urlresolvers import reverse

from nodeconductor.events import elasticsearch_dummy_client


class EventFactory(object):
    """
    Event factory that provides default data for events and add created events to elasticsearch dummy client.

    Created event fields can be accessible via .fields attribute of created event.
    """

    def __init__(self, **kwargs):
        self.create(**kwargs)
        self.save()

    def create(self, **kwargs):
        """
        Creates event fields values.

        If field is in kwargs - value from kwargs will be used for this field,
        otherwise - default value will be used for field.
        """
        self.fields = {
            '@timestamp': '2015-04-19T16:25:45.376+04:00',
            '@version': 1,
            'cloud_account_name': 'test_cloud_account_name',
            'cloud_account_uuid': 'test_cloud_account_uuid',
            'customer_abbreviation': 'TCAN',
            'customer_contact_details': 'test details',
            'customer_name': 'Test cusomter',
            'customer_uuid': 'test_customer_uuid',
            'event_type': 'test_event_type',
            'host': 'example.com',
            'importance': 'high',
            'importance_code': 30,
            'levelname': 'WARNING',
            'logger': 'nodeconductor.test',
            'message': 'Test message',
            'project_group_name': 'test_group_name',
            'project_group_uuid': 'test_group_uuid',
            'project_name': 'test_project',
            'project_uuid': 'test_project_uuid',
            'tags': ['_jsonparsefailure'],
            'type': 'gcloud-event',
            'user_uuid': 'test_user_uuid',
        }
        for key, value in kwargs.items():
            self.fields[key] = value

    def save(self):
        """ Add event to elasticsearch dummy client events """
        elasticsearch_dummy_client.ElasticsearchDummyClient.DUMMY_EVENTS.append(self.fields)

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('event-list')
