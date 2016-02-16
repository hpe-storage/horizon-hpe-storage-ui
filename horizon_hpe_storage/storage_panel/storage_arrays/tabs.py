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

from horizon_hpe_storage.storage_panel.storage_arrays \
    import license_tables as l_tables
from horizon_hpe_storage.storage_panel.storage_arrays \
    import openstack_features_tables as o_tables
from horizon_hpe_storage.storage_panel.storage_arrays \
    import capability_tables as c_tables
from horizon_hpe_storage.storage_panel.storage_arrays \
    import sched_stat_tables as sched_stat_tables


class CapabilityTab(tabs.TableTab):
    name = _("Storage Pool Capabilities")
    slug = "capabilities"
    table_classes = (c_tables.CapabilityTable,)
    template_name = ("storage_arrays/_detail_capability.html")
    preload = False

    def get_capabilities_data(self):
        pool_data = self.tab_group.kwargs['pool_data']
        capabilities = pool_data['capabilities']
        return capabilities


class SchedulerStatTab(tabs.TableTab):
    name = _("Cinder Scheduler Stats")
    slug = "sched_stats"
    table_classes = (sched_stat_tables.SchedStatsTable,)
    template_name = ("storage_arrays/_detail_sched_stats.html")
    preload = False

    def get_sched_stats_data(self):
        pool_data = self.tab_group.kwargs['pool_data']
        raw_stats = pool_data['sched_stats']
        stats = []
        for stat, value in raw_stats.iteritems():
            entry = {}
            entry["stat"] = stat
            entry["value"] = value
            stats.append(entry)
        return stats


class CapabilityTabs(tabs.TabGroup):
    slug = "capability_details"
    tabs = (CapabilityTab, SchedulerStatTab)
    # hide raw scheduler stats for now
    # tabs = (CapabilityTab,)


class LicenseTab(tabs.TableTab):
    name = _("Storage Array Licenses")
    slug = "licenses"
    table_classes = (l_tables.LicenseTable,)
    template_name = "storage_arrays/_detail_license.html"

    def get_licenses_data(self):
        system_data = self.tab_group.kwargs['system_data']
        return system_data['licenses_with_exp_dates']


class OpenstackFeaturesTab(tabs.TableTab):
    name = _("OpenStack Features")
    slug = "features"
    table_classes = (o_tables.OpenstackFeaturesTable,)
    template_name = "storage_arrays/_detail_license.html"

    def get_features_data(self):
        system_data = self.tab_group.kwargs['system_data']
        return system_data['openstack_features']


class SystemDetailTabs(tabs.TabGroup):
    slug = "system_details"
    # tabs = (OverviewTab, SystemInfoTab)
    # only show test results. System info has its own panel.
    # but keep around as example of having tabbed detail panel
    tabs = (OpenstackFeaturesTab, LicenseTab)

