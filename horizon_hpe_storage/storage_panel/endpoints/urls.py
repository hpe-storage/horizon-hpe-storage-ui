# (c) Copyright [2015] Hewlett Packard Enterprise Development LP
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from django.conf.urls import patterns
from django.conf.urls import url

from horizon_hpe_storage.storage_panel.endpoints import views

VIEWS_MOD = ('horizon_hpe_storage.storage_panel.endpoints.views')

urlpatterns = patterns(
    VIEWS_MOD,
    url(r'^(?P<volume_id>[^/]+)/link_to_volume/$',
        views.LinkVolumeView.as_view(),
        name='link_to_volume'),
    url(r'^(?P<volume_id>[^/]+)/link_to_cpg/$',
        views.LinkVolumeCPGView.as_view(),
        name='link_to_cpg'),
    url(r'^(?P<volume_id>[^/]+)/link_to_domain/$',
        views.LinkVolumeDomainView.as_view(),
        name='link_to_domain'),
    url(r'^create_endpoint/$',
        views.CreateEndpointView.as_view(),
        name='create_endpoint'),
    url(r'^(?P<service_id>[^/]+)/edit_endpoint/$',
        views.EditEndpointView.as_view(),
        name='edit_endpoint'),
)
