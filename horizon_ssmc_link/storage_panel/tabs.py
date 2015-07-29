# Copyright 2014 OpenStack Foundation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import tabs

from horizon_ssmc_link.storage_panel import tables

import horizon_ssmc_link.api.keystone_api as keystone
import horizon_ssmc_link.api.barbican_api as barbican


class EndpointsTab(tabs.TableTab):
    table_classes = (tables.EndpointsTable,)
    name = _("SSMC Links")
    slug = "endpoints_tab"
    template_name = "horizon/common/_detail_table.html"

    def get_endpoints_data(self):
        endpoints = []

        try:
            keystone_api = keystone.KeystoneAPI()
            keystone_api.do_setup(self.request)
            endpoints = keystone_api.get_ssmc_endpoints()

            # for each endpoint, get credentials
            barbican_api = barbican.BarbicanAPI()
            barbican_api.do_setup(None)
            for endpoint in endpoints:
                uname, pwd = barbican_api.get_credentials(
                    keystone_api.get_session_key(), endpoint['backend'])
                endpoint['username'] = uname

        except Exception:
            msg = _('Unable to retrieve endpoints list.')
            exceptions.handle(self.request, msg)
        return endpoints


class StorageTabs(tabs.TabGroup):
    slug = "storage_tabs"
    tabs = (EndpointsTab,)
    sticky = True
    show_single_tab = True
