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

from horizon_hpe_storage.storage_panel.endpoints \
    import tables as endpoint_tables
from horizon_hpe_storage.storage_panel.diags \
    import tables as diags_tables
from horizon_hpe_storage.storage_panel.backend_systems \
    import tables as backend_tables

import horizon_hpe_storage.api.keystone_api as keystone
import horizon_hpe_storage.api.barbican_api as barbican


class EndpointsTab(tabs.TableTab):
    table_classes = (endpoint_tables.EndpointsTable,)
    name = _("3PAR SSMC Links")
    slug = "endpoints_tab"
    template_name = "horizon/common/_detail_table.html"

    def get_endpoints_data(self):
        endpoints = []

        try:
            keystone_api = keystone.KeystoneAPI()
            keystone_api.do_setup(self.request)
            token = keystone_api.get_session_key()
            endpoints = keystone_api.get_ssmc_endpoints()

            # for each endpoint, get credentials
            barbican_api = barbican.BarbicanAPI()
            barbican_api.do_setup(None)
            for endpoint in endpoints:
                uname, pwd = barbican_api.get_credentials(
                    token, endpoint['backend'])
                endpoint['username'] = uname

        except Exception:
            msg = _('Unable to retrieve endpoints list.')
            exceptions.handle(self.request, msg)
        return endpoints


class DiagsTab(tabs.TableTab):
    table_classes = (diags_tables.DiagsTable,)
                     # endpoint_tables.EndpointsTable,)
    name = _("Cinder Diagnostics & Discovery")
    slug = "diags_tab"
    template_name = "horizon/common/_detail_table.html"

    def get_diags_data(self):
        tests = []
        sorted_tests = []

        try:
            keystone_api = keystone.KeystoneAPI()
            keystone_api.do_setup(self.request)
            token = keystone_api.get_session_key()

            # grab all tests from barbican
            barbican_api = barbican.BarbicanAPI()
            barbican_api.do_setup(None)
            tests = barbican_api.get_all_diag_tests(token)
            sorted_tests = sorted(tests, key=itemgetter('test_name'))

        except Exception as ex:
            msg = _('Unable to retrieve diagnostic test list.')
            exceptions.handle(self.request, msg)
        return sorted_tests


class BackendsTab(tabs.TableTab):
    table_classes = (backend_tables.BackendsTable,)
    name = _("Backend Storage Systems")
    slug = "backends_tab"
    template_name = "horizon/common/_detail_table.html"

    def get_backends_data(self):
        backend_systems = []

        try:
            keystone_api = keystone.KeystoneAPI()
            keystone_api.do_setup(self.request)
            token = keystone_api.get_session_key()

            # grab all tests from barbican
            barbican_api = barbican.BarbicanAPI()
            barbican_api.do_setup(None)
            tests = barbican_api.get_all_diag_tests(token)

            # now generate backend system info from tests
            for test in tests:
                config_status = test['config_test_status']
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
                                data['test_name'] = test['test_name']
                                backend_systems.append(data)

            backend_systems = self.trim_backend_list(backend_systems)

        except Exception as ex:
            msg = _('Unable to retrieve diagnostic test list.')
            exceptions.handle(self.request, msg)

        return backend_systems

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

    def trim_backend_list(self, cur_backend_list):
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


class StorageTabs(tabs.TabGroup):
    slug = "storage_tabs"
    tabs = (EndpointsTab, DiagsTab, BackendsTab)
    sticky = True
    # show_single_tab = True
