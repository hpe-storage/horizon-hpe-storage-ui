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

from horizon_hpe_storage.storage_panel.backend_systems import views

VIEWS_MOD = ('horizon_hpe_storage.storage_panel.backend_systems.views')

urlpatterns = patterns(
    VIEWS_MOD,
    url(r'^$',
        views.IndexView.as_view(),
        name='index'),
    url(r'^(?P<pool_name>[^/]+)/$',
        views.PoolDetailView.as_view(),
        name='pool_details'),
    url(r'^(?P<system_info>[^/]+)/license_detail$',
        views.LicenseDetailView.as_view(),
        name='license_detail'),
    url(r'^(?P<pool_name>[^/]+)/capability_detail$',
        views.PoolDetailView.as_view(),
        name='capability_detail'),
)
