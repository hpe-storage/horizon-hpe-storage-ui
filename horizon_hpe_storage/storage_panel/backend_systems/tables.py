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

from django.core.urlresolvers import NoReverseMatch  # noqa
from django.core.urlresolvers import reverse
from django.utils import html
from django.utils.translation import ugettext_lazy as _
from django.utils import safestring

from horizon import forms
from horizon import tables

from horizon_hpe_storage.storage_panel.backend_systems import tabs


class LicenseLink(tables.LinkAction):
    name = "licenses"
    verbose_name = _("View License Information")
    classes = ("btn-log",)

    def get_link_url(self, datum):
        link_url = "backend_systems/" + \
            datum['name'] + "::" + datum['test_name'] + "/license_detail"
        # tab_query_string = tabs.LicenseTab(
        #     tabs.BackendDetailTabs).get_query_string()
        # return "?".join([base_url, tab_query_string])
        return link_url

def get_pool_name(pool_name):
    try:
        url = reverse("horizon:admin:hpe_storage:backend_systems:" + \
                      "pool_details", args=(pool_name,)) + "capability_detail"
        pool = '<a href="%s">%s</a>' % (url, html.escape(pool_name))
    except NoReverseMatch:
        pool = html.escape(pool_name)
    return pool


class PoolsColumn(tables.Column):
    # Customized column class.
    def get_raw_data(self, backend_system):
        link = _('%(pool_name)s')
        pool_name_start = backend_system['host_name'] + "@"
        pools = []
        for cinder_host in backend_system['cinder_hosts']:
            pool_name = get_pool_name(pool_name_start + cinder_host)
            vals = {"pool_name": pool_name}
            pools.append(link % vals)

        return safestring.mark_safe("<br>".join(pools))

class BackendsTable(tables.DataTable):
    system_name = tables.Column(
        'name',
        verbose_name=_('System Name'),
        form_field=forms.CharField(max_length=64))
    system_ip = tables.Column(
        'ip_address',
        verbose_name=_('IP Address'),
        form_field=forms.CharField(max_length=64))
    model = tables.Column(
        'model',
        verbose_name=_('Model'),
        form_field=forms.CharField(max_length=64))
    serial_number = tables.Column(
        'serial_number',
        verbose_name=_('Serial Number'),
        form_field=forms.CharField(max_length=64))
    os_version = tables.Column(
        'os_version',
        verbose_name=_('OS Version'),
        form_field=forms.CharField(max_length=64))
    wsapi_version = tables.Column(
        'wsapi_version',
        verbose_name=_('WSAPI Version'),
        form_field=forms.CharField(max_length=64))
    pools = PoolsColumn(
        "pools",
        verbose_name=_("Cinder Hosts"),
        wrap_list=True)

    def get_object_id(self, backend_system):
        return backend_system['name'] + "::" + backend_system['test_name']

    class Meta(object):
        name = "backends"
        verbose_name = _("Backend Storage Systems Discovered via "
                         "Cinder Diagnostic Tests")
        hidden_title = False
        row_actions = (LicenseLink,)
