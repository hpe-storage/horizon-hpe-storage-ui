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

from horizon_hpe_storage.storage_panel.endpoints \
    import urls as endpoint_urls
from horizon_hpe_storage.storage_panel.diags \
    import urls as diag_urls

from horizon_hpe_storage.storage_panel import views

urlpatterns = patterns(
    '',
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^\?tab=storage_tabs$',
        views.IndexView.as_view(), name='endpoints_tab'),
    url(r'^\?tab=storage_tabs$',
        views.IndexView.as_view(), name='diags_tab'),
    url(r'', include(endpoint_urls, namespace='endpoints')),
    url(r'diags/', include(diag_urls, namespace='diags')),
)
