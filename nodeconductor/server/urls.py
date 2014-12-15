from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import patterns
from django.conf.urls import include
from django.conf.urls import url
from django.contrib import admin
import permission

from nodeconductor.core.routers import SortedDefaultRouter as DefaultRouter
from nodeconductor.backup import urls as backup_urls
from nodeconductor.iaas import urls as iaas_urls
from nodeconductor.structure import urls as structure_urls


admin.autodiscover()
permission.autodiscover()

router = DefaultRouter()
iaas_urls.register_in(router)
structure_urls.register_in(router)
backup_urls.register_in(router)


urlpatterns = patterns(
    '',
    url(r'^admin/', include(admin.site.urls), name='admin'),
    url(r'^api/', include(router.urls)),
    url(r'^api/', include('nodeconductor.iaas.urls')),
    url(r'^api/', include('nodeconductor.structure.urls')),
    url(r'^api/version/', 'nodeconductor.core.views.version_detail'),
    url(r'^api-auth/password/', 'nodeconductor.core.views.obtain_auth_token'),
    url(r'^api-auth/saml2/', 'nodeconductor.core.views.assertion_consumer_service'),
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
)

# FIXME: This shouldn't be here
if 'nc_admin.base' in settings.INSTALLED_APPS:
    urlpatterns += patterns(
        '',
        url(r'^', include('nc_admin.base.urls')))

if settings.DEBUG:
    (r'^%{static_url}/(?P<path>.*)$'.format(static_url=settings.STATIC_URL),
        'django.views.static.serve', {'document_root': settings.STATIC_ROOT}),
