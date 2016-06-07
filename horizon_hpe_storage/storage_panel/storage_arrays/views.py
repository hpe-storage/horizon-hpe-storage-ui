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
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.utils import safestring

from horizon import exceptions
from horizon import forms
from horizon import tables
from horizon import tabs
from horizon.utils import memoized

from horizon_hpe_storage.storage_panel import tabs as storage_tabs
from horizon_hpe_storage.storage_panel.storage_arrays \
    import tabs as array_tabs
from horizon_hpe_storage.storage_panel.diags import forms as diag_forms

import horizon_hpe_storage.api.keystone_api as keystone
import horizon_hpe_storage.api.barbican_api as barbican
import horizon_hpe_storage.api.cinder_api as local_cinder

from openstack_dashboard.api import cinder

import collections
import logging
import time

LOG = logging.getLogger(__name__)


class IndexView(tables.DataTableView):
    tab_group_class = storage_tabs.StorageTabs
    template_name = 'storage_arrays/index.html'
    # page_title = _("HP Storage")


class DiscoverArraysView(forms.ModalFormView):
    form_class = diag_forms.TestAllCinder
    modal_header = _("Discover Storage Arrays")
    modal_id = "test_all_cinder_modal"
    template_name = 'storage_arrays/discover_arrays.html'
    submit_label = _("Discover Storage Arrays")
    submit_url = reverse_lazy(
        "horizon:admin:hpe_storage:diags:test_all_cinder_nodes")
    success_url = reverse_lazy('horizon:admin:hpe_storage:index')
    page_title = _("Discover Storage Arrays")


class PoolDetailView(tabs.TabView):
    tab_group_class = array_tabs.CapabilityTabs
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
            keystone_api = keystone.KeystoneAPI()
            keystone_api.do_setup(self.request)
            cinder_api = local_cinder.CinderAPI()
            cinder_api.do_setup(None)

            pool_data = {}
            pool_name = self.kwargs['pool_name']
            pools = cinder.pool_list(self.request, detailed=True)
            for pool in pools:
                if pool.name == pool_name:
                    pool_data['name'] = pool_name

                    capabilities = cinder_api.get_capabilities(
                        keystone_api.get_token_id(),
                        keystone_api.get_tenant_id(),
                        pool_name)
                    pool_data['capabilities'] = capabilities

                    pool_data['sched_stats'] = \
                        self.format_sched_stats(
                            pool._apiresource._info['capabilities'])
                    # if hasattr(pool, 'free_capacity_gb'):
                    #     pool_data['free_capacity_gb'] = pool.free_capacity_gb
                    break
            if not pool_data:
                raise Exception("No pool data for cinder host: " + pool_name)
            else:
                pool_data = self.determine_enabled_capabilities(pool_data)

        except Exception as ex:
            redirect = self.get_redirect_url()
            exceptions.handle(self.request,
                              _('Unable to retrieve storage pool data'),
                              redirect=redirect)
        return pool_data

    def format_sched_stats(self, stats):
        formatted_stats = collections.OrderedDict()

        # first stat should be time the stats were collected
        formatted_stats['Stats Collection Time'] = stats['timestamp']

        # next should be all the booleans
        non_bools = {}
        for key, value in stats.iteritems():
            if isinstance(value, bool):
                formatted_stats[key] = value
            else:
                if isinstance(value, list):
                    value = ", ".join(map(str, value))
                non_bools[key] = value

        full_list = formatted_stats.copy()
        full_list.update(non_bools)
        return full_list

    def determine_enabled_capabilities(self, pool_data):
        # go through each capability and determine if we support it from
        # values in scheduler stats (this is hardcoded)
        capabilities = pool_data['capabilities']
        sched_stats = pool_data['sched_stats']
        new_capabilities = []

        for capability in capabilities:
            new_capability = {}
            new_capability['name'] = capability['name']
            new_capability['description'] = capability['description']
            capability_name = capability['name'].lower()
            if capability_name == "replication":
                if 'replication_enabled' in sched_stats:
                    new_capability['enabled'] = \
                        "%r" % (sched_stats['replication_enabled'])
                else:
                    new_capability['enabled'] = 'Undetermined'
            elif capability_name == "qos":
                if 'QoS_support' in sched_stats:
                    new_capability['enabled'] = \
                        "%r" % (sched_stats['QoS_support'])
                else:
                    new_capability['enabled'] = 'Undetermined'
            elif capability_name == "thin provisioning":
                if 'thin_provisioning_support' in sched_stats:
                    new_capability['enabled'] = \
                        "%r" % (sched_stats['thin_provisioning_support'])
                else:
                    new_capability['enabled'] = 'Undetermined'
            else:
                new_capability['enabled'] = 'Undetermined'

            new_capabilities.append(new_capability)

        pool_data['capabilities'] = new_capabilities
        return pool_data

    def get_redirect_url(self):
        return reverse('horizon:admin:hpe_storage:index')

    def get_tabs(self, request, *args, **kwargs):
        pool_data = self.get_data()
        return self.tab_group_class(request, pool_data=pool_data, **kwargs)


class LicenseDetailView(tabs.TabView):
    tab_group_class = array_tabs.SystemDetailTabs
    template_name = 'horizon/common/_detail.html'
    page_title = "{{ system_name }}"
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

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
            self.keystone_api.do_setup(self.request)
            self.barbican_api.do_setup(self.keystone_api.get_session())

            test = self.barbican_api.get_node(
                self.keystone_api.get_session_key(),
                test_name, barbican.CINDER_NODE_TYPE)

            # find the 'system info' for our backend system
            config_status = test['diag_test_status']
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
        return self.tab_group_class(
            request,
            license_data=license_data,
            **kwargs)


class SystemDetailView(tabs.TabView):
    tab_group_class = array_tabs.SystemDetailTabs
    template_name = 'horizon/common/_detail.html'
    page_title = "{{ system_info.name }}"
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def get_context_data(self, **kwargs):
        context = super(SystemDetailView, self).get_context_data(**kwargs)
        system_info = self.get_data()
        context['system_info'] = system_info
        context['url'] = self.get_redirect_url()
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            backend_storage_info = self.kwargs['backend_storage_info']
            items = backend_storage_info.split("::")
            system_name = items[0]
            test_name = items[1]

            self.keystone_api.do_setup(self.request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            tests = self.barbican_api.get_all_nodes(
                barbican.CINDER_NODE_TYPE)

            # now generate backend system info from tests
            for test in tests:
                if test['node_name'] == test_name:
                    config_status = test['diag_test_status']
                    backends = config_status.split("Backend Section:")
                    for backend in backends:
                        if backend:
                            raw_results = backend.split("::")
                            disp_results = {}
                            disp_results['backend_name'] = \
                                "[" + raw_results[0] + "]"
                            for raw_result in raw_results:
                                if raw_result.startswith('system_info'):
                                    data = self.get_backend_system_info(
                                        raw_result[12:])
                                    if data['name'] == system_name:
                                        data = \
                                            self.update_license_info(data)
                                        data = \
                                            self.add_openstack_features(data)
                                        return data

        except Exception as ex:
            redirect = self.get_redirect_url()
            exceptions.handle(self.request,
                              _('Unable to retrieve storage system data'),
                              redirect=redirect)
        return None

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

    def update_license_info(self, data):
        license_list = data['licenses']
        licenses = []

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

        data['licenses_with_exp_dates'] = licenses
        return data

    def license_enabled(self, data, license_name):
        license_list = data['licenses']
        for license in license_list:
            items = license.split("//")
            name = items[0]
            if name.startswith(license_name):
                return True

        return False

    def add_openstack_features(self, data):
        license_list = data['licenses']

        features = [
            {"name": "Virtual Volumes",
             "requirements": "Virtual Copy,Thin Provisioning"},
            {"name": "Flash Cache", "requirements": "Adaptive Flash Cache"},
            {"name": "Volume Migration",
             "requirements": "Dynamic Optimization"},
            {"name": "Volume Retype", "requirements": "Dynamic Optimization"},
            {"name": "Manage Volume", "requirements": "Dynamic Optimization"},
            {"name": "Volume Snapshots", "requirements": "Virtual Copy"},
            {"name": "Shares", "requirements": "File Persona Basic"},
            # TODO data compaction assoicated with backup?
            # { "name": "Data Compaction",
            #   "requirements": "Adaptive Optimization,Dynamic Optimization"},
            {"name": "Volume Replication", "requirements": "Remote Copy"},
        ]

        for feature in features:
            requirements = feature['requirements'].split(",")
            enabled = True
            for requirement in requirements:
                if not self.license_enabled(data, requirement):
                    enabled = False

            feature['requirements'] = \
                safestring.mark_safe("<br>".join(requirements))
            feature['enabled'] = enabled

        data['openstack_features'] = features
        return data

    def get_redirect_url(self):
        return reverse('horizon:admin:hpe_storage:index')

    def get_tabs(self, request, *args, **kwargs):
        system_data = self.get_data()
        return self.tab_group_class(request, system_data=system_data, **kwargs)
