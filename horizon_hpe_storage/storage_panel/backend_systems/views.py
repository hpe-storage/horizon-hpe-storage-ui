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

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import tables
from horizon import tabs
from horizon.utils import memoized

from horizon_hpe_storage.storage_panel import tabs as storage_tabs
from horizon_hpe_storage.storage_panel.backend_systems \
    import tabs as backend_tabs

import horizon_hpe_storage.api.keystone_api as keystone
import horizon_hpe_storage.api.barbican_api as barbican

from openstack_dashboard.api import cinder


import logging
import time

LOG = logging.getLogger(__name__)


class IndexView(tables.DataTableView):
    tab_group_class = storage_tabs.StorageTabs
    template_name = 'backend_systems/index.html'
    # page_title = _("HP Storage")


class PoolDetailView(tabs.TabView):
    tab_group_class = backend_tabs.CapabilityTabs
    template_name = 'horizon/common/_detail.html'
    page_title = "{{ pool_data.name }}"

    def get_context_data(self, **kwargs):
        context = super(PoolDetailView, self).get_context_data(**kwargs)
        pool_data = self.get_data()
        context['pool_data'] = pool_data
        context['url'] = self.get_redirect_url()
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            pool_data = {}
            pool_name = self.kwargs['pool_name']
            pools = cinder.pool_list(self.request, detailed=True)
            for pool in pools:
                if pool.name == pool_name:
                    pool_data['name'] = pool_name
                    pool_data['capabilities'] = \
                        pool._apiresource._info['capabilities']
                    # if hasattr(pool, 'free_capacity_gb'):
                    #     pool_data['free_capacity_gb'] = pool.free_capacity_gb
                    break
            if not pool_data:
                raise Exception("No pool data for cinder host: " + pool_name)

        except Exception:
            redirect = self.get_redirect_url()
            exceptions.handle(self.request,
                              _('Unable to retrieve storage pool data'),
                              redirect=redirect)
        return pool_data

    def get_redirect_url(self):
        return reverse('horizon:admin:hpe_storage:index')

    def get_tabs(self, request, *args, **kwargs):
        pool_data = self.get_data()
        return self.tab_group_class(request, pool_data=pool_data, **kwargs)


class LicenseDetailView(tabs.TabView):
    tab_group_class = backend_tabs.BackendDetailTabs
    template_name = 'horizon/common/_detail.html'
    page_title = "{{ system_name }}"

    def get_context_data(self, **kwargs):
        context = super(LicenseDetailView, self).get_context_data(**kwargs)
        items = kwargs['system_info'].split("::")
        system_name = items[0]
        license_data = {}
        licenses = self.get_data()
        license_data['licenses'] = licenses
        context['system_name'] = system_name
        context['license_data'] = license_data
        context['url'] = self.get_redirect_url()
        return context

    @memoized.memoized_method
    def get_data(self):
        items = self.kwargs['system_info'].split("::")
        system_name = items[0]
        test_name = items[1]

        licenses = []
        try:
            # get data from associated cinder.conf test results
            keystone_api = keystone.KeystoneAPI()
            keystone_api.do_setup(self.request)
            barbican_api = barbican.BarbicanAPI()
            barbican_api.do_setup(None)

            test = barbican_api.get_diag_test(
                keystone_api.get_session_key(),
                'cinderdiags-' + test_name)

            # find the 'system info' for our backend system
            config_status = test['config_test_status']
            backend_system = None
            backends = config_status.split("Backend Section:")
            for backend in backends:
                if backend:
                    raw_results = backend.split("::")
                    disp_results = {}
                    disp_results['backend_name'] = "[" + raw_results[0] + "]"
                    for raw_result in raw_results:
                        if raw_result.startswith('system_info'):
                            data = self.get_backend_system_info(
                                raw_result[12:])
                            if data:
                                if data['name'] == system_name:
                                    backend_system = data
                                    break

                    if backend_system:
                        break

            if backend_system:
                license_list = backend_system['licenses']

                for license in license_list:
                    exp_date = "-"
                    items = license.split("//")
                    name = items[0]
                    if len(items) > 1:
                        secs = items[1]
                        exp_date = time.strftime('%Y-%m-%d %H:%M:%S',
                                                 time.localtime(float(secs)))
                    entry = {'license': name,
                             'exp_date': exp_date}
                    licenses.append(entry)

        except Exception as ex:
            redirect = self.get_redirect_url()
            exceptions.handle(self.request,
                              _('Unable to retrieve license keys.'),
                              redirect=redirect)

        return licenses

    def get_backend_system_info(self, data):
        # pull all of the data out
        disp_results = {}
        items = data.split(";;")
        for item in items:
            key, value = item.split(":")
            if key == "licenses":
                licenses = value.split(";")
                disp_results[key] = licenses
            else:
                disp_results[key] = value

        return disp_results

    def get_redirect_url(self):
        return reverse('horizon:admin:hpe_storage:index')

    def get_tabs(self, request, *args, **kwargs):
        license_data = {}
        licenses = self.get_data()
        license_data['licenses'] = licenses
        return self.tab_group_class(request, license_data=license_data, **kwargs)

