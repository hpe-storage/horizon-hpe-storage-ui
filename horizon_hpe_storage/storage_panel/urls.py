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

from horizon_hpe_storage.storage_panel.overview \
    import urls as overview_urls
from horizon_hpe_storage.storage_panel.config \
    import urls as config_urls
from horizon_hpe_storage.storage_panel.diags \
    import urls as diag_urls
from horizon_hpe_storage.storage_panel.storage_arrays \
    import urls as array_urls

from horizon_hpe_storage.storage_panel import views

urlpatterns = patterns(
    '',
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^\?tab=storage_tabs$',
        views.IndexView.as_view(), name='config_tab'),
    url(r'^\?tab=storage_tabs$',
        views.IndexView.as_view(), name='diags_tab'),
    url(r'overview/',
        include(overview_urls, namespace='overview')),
    url(r'config/',
        include(config_urls, namespace='config')),
    url(r'diags/',
        include(diag_urls, namespace='diags')),
    url(r'^storage_arrays/',
        include(array_urls, namespace='storage_arrays')),
)
