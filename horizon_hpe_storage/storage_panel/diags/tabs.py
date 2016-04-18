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

from horizon_hpe_storage.storage_panel.diags \
    import test_results_tables as test_tables

import horizon_hpe_storage.api.barbican_api as barbican


class CinderOverviewTab(tabs.TableTab):
    name = _("Diagnostic Test Results")
    slug = "cinder_overview"
    table_classes = (test_tables.TestDescriptionTable,
                     test_tables.BackendTestTable,
                     test_tables.SoftwareTestTable)
    template_name = ("diags/cinder_test_result_tables.html")

    def get_test_descriptions_data(self):
        test = self.tab_group.kwargs['test']
        test_data = None
        if test['service_type'] == barbican.CINDER_NODE_TYPE:
            test_data = test['test_descriptions']
        return test_data

    def get_backend_test_results_data(self):
        test = self.tab_group.kwargs['test']
        test_data = None
        if test['service_type'] == barbican.CINDER_NODE_TYPE:
            test_data = test['test_table_data']
        return test_data

    def get_software_test_results_data(self):
        test = self.tab_group.kwargs['test']
        test_data = test['formatted_software_test_results']
        return test_data


class NovaOverviewTab(tabs.TableTab):
    name = _("Diagnostic Test Results")
    slug = "nova_overview"
    table_classes = (test_tables.SoftwareTestTable,)
    template_name = ("diags/nova_test_result_tables.html")

    def get_software_test_results_data(self):
        test = self.tab_group.kwargs['test']
        test_data = test['formatted_software_test_results']
        return test_data


class ConfigItemsTab(tabs.Tab):
    name = _("Driver Configuration Entries")
    slug = "config_entries"
    template_name = ("diags/_config_items.html")

    def get_context_data(self, request):
        return {"test": self.tab_group.kwargs['test']}


class RawTestDumpTab(tabs.Tab):
    name = _("Raw Test Results Data")
    slug = "raw_test"
    template_name = ("diags/_raw_test.html")

    def get_context_data(self, request):
        return {"test": self.tab_group.kwargs['test']}


class TEMPSystemInfoTab(tabs.Tab):
    name = _("Storage System Information")
    slug = "systems"
    template_name = ("diags/_system_overview.html")

    def get_context_data(self, request):
        return {"test": self.tab_group.kwargs['test']}


class CinderTestDetailTabs(tabs.TabGroup):
    slug = "cinder_test_details"
    tabs = (CinderOverviewTab, ConfigItemsTab, RawTestDumpTab)


class NovaTestDetailTabs(tabs.TabGroup):
    slug = "nova_test_details"
    tabs = (NovaOverviewTab, RawTestDumpTab)
