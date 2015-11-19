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
from horizon.utils import functions as utils

from horizon_hpe_storage.storage_panel.endpoints \
    import tables as endpoint_tables
from horizon_hpe_storage.storage_panel.diags \
    import tables as diags_tables

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
    name = _("Cinder Diagnostics")
    slug = "diags_tab"
    template_name = "horizon/common/_detail_table.html"

    def get_diags_data(self):
        tests = []

        try:
            keystone_api = keystone.KeystoneAPI()
            keystone_api.do_setup(self.request)
            token = keystone_api.get_session_key()

            # grab all test from barbican
            barbican_api = barbican.BarbicanAPI()
            barbican_api.do_setup(None)
            tests = barbican_api.get_all_diag_tests(token)
            sorted_tests = sorted(tests, key=itemgetter('test_name'))

        except Exception:
            msg = _('Unable to retrieve diagnostic test list.')
            exceptions.handle(self.request, msg)
        return sorted_tests


class StorageTabs(tabs.TabGroup):
    slug = "storage_tabs"
    tabs = (EndpointsTab, DiagsTab)
    sticky = True
    show_single_tab = True
