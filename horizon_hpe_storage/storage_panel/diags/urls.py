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

from horizon_hpe_storage.storage_panel.diags import views

VIEWS_MOD = ('horizon_hpe_storage.storage_panel.diags.views')

urlpatterns = patterns(
    VIEWS_MOD,
    url(r'^$',
        views.IndexView.as_view(),
        name='index'),
    url(r'^(?P<node_name>[^/]+)/test_cinder_node/$',
        views.TestCinderView.as_view(),
        name='test_cinder_node'),
    url(r'^test_all_cinder_nodes/$',
        views.TestAllCinderView.as_view(),
        name='test_all_cinder_nodes'),
    url(r'^(?P<node_name>[^/]+)/test_nova_node/$',
        views.TestNovaView.as_view(),
        name='test_nova_node'),
    url(r'^test_all_nova_nodes/$',
        views.TestAllNovaView.as_view(),
        name='test_all_nova_nodes'),

    url(r'^(?P<node_name>[^/]+)/$',
        views.CinderTestDetailView.as_view(),
        name='cinder_test_detail'),
    url(r'^(?P<node_name>[^/]+)/cinder_test_details$',
        views.CinderTestDetailView.as_view(),
        name='cinder_test_details'),

    url(r'^(?P<node_name>[^/]+)/$',
        views.NovaTestDetailView.as_view(),
        name='nova_test_detail'),
    url(r'^(?P<node_name>[^/]+)/nova_test_details$',
        views.NovaTestDetailView.as_view(),
        name='nova_test_details'),
)
