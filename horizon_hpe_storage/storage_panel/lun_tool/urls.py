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


from horizon_hpe_storage.storage_panel.lun_tool import views

VIEWS_MOD = ('horizon_hpe_storage.storage_panel.lun_tool.views')

urlpatterns = patterns(
    VIEWS_MOD,
    url(r'^$',
        views.IndexView.as_view(),
        name='index'),
    url(r'^(?P<timestamp>[^/]+)/path_detail$',
        views.PathDetailView.as_view(),
        name='path_detail'),
    url(r'^run_lun_tool/$',
        views.RunLunToolView.as_view(),
        name='run_lun_tool'),
    url(r'^manage_os_vars/$',
        views.ManageOSVarsView.as_view(),
        name='manage_os_vars'),
    url(r'^(?P<timestamp>[^/]+)/show_diff/$',
        views.ShowDiffView.as_view(),
        name='show_diff'),
    url(r'^(?P<timestamp>[^/]+)/diff_details$',
        views.DiffDetailView.as_view(),
        name='diff_details'),
)
