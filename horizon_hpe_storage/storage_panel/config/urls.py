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

from django.conf.urls import include
from django.conf.urls import patterns
from django.conf.urls import url

from horizon_hpe_storage.storage_panel.config import views
from horizon_hpe_storage.storage_panel.config.software_tests \
    import urls as software_test_urls

VIEWS_MOD = ('horizon_hpe_storage.storage_panel.config.views')

urlpatterns = patterns(
    VIEWS_MOD,
    url(r'^$',
        views.IndexView.as_view(),
        name='index'),

    url(r'^(?P<volume_id>[^/]+)/link_to_volume/$',
        views.LinkVolumeView.as_view(),
        name='link_to_volume'),
    url(r'^(?P<volume_id>[^/]+)/link_to_volume_cpg/$',
        views.LinkVolumeCPGView.as_view(),
        name='link_to_volume_cpg'),
    url(r'^(?P<volume_id>[^/]+)/link_to_volume_domain/$',
        views.LinkVolumeDomainView.as_view(),
        name='link_to_volume_domain'),
    url(r'^(?P<snapshot_id>[^/]+)/link_to_snapshot/$',
        views.LinkSnapshotView.as_view(),
        name='link_to_snapshot'),
    url(r'^create_endpoint/$',
        views.CreateEndpointView.as_view(),
        name='create_endpoint'),
    url(r'^(?P<service_id>[^/]+)/edit_endpoint/$',
        views.EditEndpointView.as_view(),
        name='edit_endpoint'),

    url(r'^(?P<node_type>[^/]+)/software_tests/',
        include(software_test_urls, namespace='software_tests')),

    url(r'^register_cinder_node/$',
        views.RegisterCinderView.as_view(),
        name='register_cinder_node'),
    url(r'^(?P<node_name>[^/]+)/edit_cinder_node/$',
        views.EditCinderView.as_view(),
        name='edit_cinder_node'),
    url(r'^(?P<node_name>[^/]+)/validate_cinder_node/$',
        views.ValidateCinderView.as_view(),
        name='validate_cinder_node'),
    url(r'^validate_all_cinder_nodes/$',
        views.ValidateAllCinderView.as_view(),
        name='validate_all_cinder_nodes'),

    url(r'^register_nova_node/$',
        views.RegisterNovaView.as_view(),
        name='register_nova_node'),
    url(r'^(?P<node_name>[^/]+)/edit_nova_node/$',
        views.EditNovaView.as_view(),
        name='edit_nova_node'),
    url(r'^(?P<node_name>[^/]+)/validate_nova_node/$',
        views.ValidateNovaView.as_view(),
        name='validate_nova_node'),
    url(r'^validate_all_nova_nodes/$',
        views.ValidateAllNovaView.as_view(),
        name='validate_all_nova_nodes'),
)
