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

from django.utils.translation import ugettext_lazy as _
from operator import itemgetter

from horizon import exceptions
from horizon import tabs

from horizon_hpe_storage.storage_panel.overview \
    import tables as overview_tables
from horizon_hpe_storage.storage_panel.config \
    import tables as config_tables
from horizon_hpe_storage.storage_panel.diags \
    import tables as diags_tables
from horizon_hpe_storage.storage_panel.storage_arrays \
    import tables as arrays_tables


import horizon_hpe_storage.api.keystone_api as keystone
import horizon_hpe_storage.api.barbican_api as barbican


class ConfigTab(tabs.TableTab):
    table_classes = (config_tables.EndpointsTable,
                     config_tables.CinderNodeTable,
                     config_tables.NovaNodeTable,)
    name = _("Configuration")
    slug = "config_tab"
    template_name = "config/config_tables.html"
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def get_endpoints_data(self):
        endpoints = []

        try:
            self.keystone_api.do_setup(self.request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            endpoints = self.keystone_api.get_ssmc_endpoints()

            # for each endpoint, get credentials
            for endpoint in endpoints:
                uname, pwd = self.barbican_api.get_ssmc_credentials(
                    endpoint['backend'])
                endpoint['username'] = uname

        except Exception as ex:
            msg = _('Unable to retrieve endpoints list.')
            exceptions.handle(self.request, msg)
        return endpoints

    def get_reg_cinder_nodes_data(self):
        sorted_nodes = []

        try:
            self.keystone_api.do_setup(self.request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            nodes = self.barbican_api.get_all_nodes(
                barbican.CINDER_NODE_TYPE)
            sorted_nodes = sorted(nodes, key=itemgetter('node_name'))

        except Exception as ex:
            msg = _('Unable to retrieve Cinder Node list.')
            exceptions.handle(self.request, msg)
        return sorted_nodes


    def get_reg_nova_nodes_data(self):
        sorted_nodes = []

        try:
            self.keystone_api.do_setup(self.request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            nodes = self.barbican_api.get_all_nodes(
                barbican.NOVA_NODE_TYPE)
            sorted_nodes = sorted(nodes, key=itemgetter('node_name'))

        except Exception as ex:
            msg = _('Unable to retrieve Nova Node list.')
            exceptions.handle(self.request, msg)
        return sorted_nodes


class DiagsTab(tabs.TableTab):
    table_classes = (diags_tables.CinderNodeTable,
                     diags_tables.NovaNodeTable,)
    name = _("Diagnostic Tests")
    slug = "diags_tab"
    template_name = "diags/diag_tables.html"
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def get_diag_cinder_nodes_data(self):
        sorted_nodes = []

        try:
            self.keystone_api.do_setup(self.request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            nodes = self.barbican_api.get_all_nodes(
                barbican.CINDER_NODE_TYPE)
            sorted_nodes = sorted(nodes, key=itemgetter('node_name'))

        except Exception as ex:
            msg = _('Unable to retrieve Cinder Node list.')
            exceptions.handle(self.request, msg)
        return sorted_nodes


    def get_diag_nova_nodes_data(self):
        sorted_nodes = []

        try:
            self.keystone_api.do_setup(self.request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            nodes = self.barbican_api.get_all_nodes(
                barbican.NOVA_NODE_TYPE)
            sorted_nodes = sorted(nodes, key=itemgetter('node_name'))

        except Exception as ex:
            msg = _('Unable to retrieve Nova Node list.')
            exceptions.handle(self.request, msg)
        return sorted_nodes


class ArraysTab(tabs.TableTab):
    table_classes = (arrays_tables.StorageArraysTable,)
    name = _("Storage Arrays")
    slug = "arrays_tab"
    template_name = "horizon/common/_detail_table.html"
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def get_storage_arrays_data(self):
        storage_arrays = []

        try:
            self.keystone_api.do_setup(self.request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            nodes = self.barbican_api.get_all_nodes(
                barbican.CINDER_NODE_TYPE)

            # now generate backend system info from tests
            for node in nodes:
                if 'diag_test_status' in node:
                    config_status = node['diag_test_status']
                    backends = config_status.split("Backend Section:")
                    for backend in backends:
                        if backend:
                            raw_results = backend.split("::")
                            disp_results = {}
                            disp_results['backend_name'] = "[" + raw_results[0] + "]"
                            for raw_result in raw_results:
                                if raw_result.startswith('system_info'):
                                    data = self.get_storage_array_info(
                                        raw_result[12:])
                                    data['test_name'] = node['node_name']
                                    storage_arrays.append(data)

            storage_arrays = self.trim_array_list(storage_arrays)

        except Exception as ex:
            msg = _('Unable to retrieve backend storage arrays.')
            exceptions.handle(self.request, msg)

        return storage_arrays

    def get_storage_array_info(self, data):
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

    def trim_array_list(self, cur_backend_list):
        # modify our list to include list of cinder hosts
        temp_backend_list = []
        for cur_backend in cur_backend_list:
            cinder_hosts = []
            cur_cpgs = cur_backend['cpgs'].split(',')
            for cpg in cur_cpgs:
                cinder_host = cur_backend['backend'] + "#" + cpg
                cinder_hosts.append(cinder_host)
            cur_backend['cinder_hosts'] = cinder_hosts
            temp_backend_list.append(cur_backend)

        new_backend_list = []
        # we only want to show each system once, but we need to combine all the
        # cinder hosts (host@backen#cpg) for the system
        for cur_backend in temp_backend_list:
            is_dup = False
            for new_backend in new_backend_list:
                if cur_backend['serial_number'] == new_backend['serial_number']:
                    # this system already exists in out list
                    is_dup = True
                    for cur_cinder_host in cur_backend['cinder_hosts']:
                        add_cinder_host = True
                        for new_cinder_host in new_backend['cinder_hosts']:
                            if cur_cinder_host == new_cinder_host:
                                # already exists
                                add_cinder_host = False
                                break
                        if add_cinder_host:
                            # update the cinder hosts for the new list
                            new_backend['cinder_hosts'].append(cur_cinder_host)

            if not is_dup:
                new_backend_list.append(cur_backend)

        return new_backend_list


class OverviewTab(tabs.TableTab):
    name = _("Overview")
    slug = "overview_tab"
    template_name = "overview/index.html"
    table_classes = (overview_tables.OverviewTable,)

    def get_overview_panel_data(self):
        list = []
        return list


class StorageTabs(tabs.TabGroup):
    slug = "storage_tabs"
    tabs = (OverviewTab, ConfigTab, DiagsTab, ArraysTab)
    sticky = True
    # show_single_tab = True
