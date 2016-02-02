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

from horizon import tabs

from horizon_hpe_storage.storage_panel.backend_systems \
    import license_tables as l_tables
from horizon_hpe_storage.storage_panel.backend_systems \
    import capability_tables as c_tables


class CapabilityTab(tabs.TableTab):
    name = _("Storage Pool Capabilities")
    slug = "capabilities"
    table_classes = (c_tables.CapabilityTable,)
    template_name = ("backend_systems/_detail_capability.html")
    preload = False

    def get_capabilities_data(self):
        pool_data = self.tab_group.kwargs['pool_data']
        raw_capabilities = pool_data['capabilities']
        capabilities = []
        for capability, value in raw_capabilities.iteritems():
            entry = {}
            entry["capability"] = capability
            entry["value"] = value
            capabilities.append(entry)
        return capabilities


class CapabilityTabs(tabs.TabGroup):
    slug = "capability_details"
    tabs = (CapabilityTab,)


class LicenseTab(tabs.TableTab):
    name = _("Licenses")
    slug = "licenses"
    table_classes = (l_tables.LicenseTable,)
    template_name = "backend_systems/_detail_license.html"
    preload = False

    def get_licenses_data(self):
        license_data = self.tab_group.kwargs['license_data']
        return license_data['licenses']


class BackendDetailTabs(tabs.TabGroup):
    slug = "backend_details"
    # tabs = (OverviewTab, SystemInfoTab)
    # only show test results. System info has its own panel.
    # but keep around as example of having tabbed detail panel
    tabs = (LicenseTab,)

