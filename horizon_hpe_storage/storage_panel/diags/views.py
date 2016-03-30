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
from horizon.utils import memoized

from horizon_hpe_storage.storage_panel.diags import forms as diag_forms

from horizon import tabs

from horizon_hpe_storage.storage_panel import tabs as storage_tabs
from horizon_hpe_storage.storage_panel.diags import tabs as diags_tabs

import horizon_hpe_storage.api.keystone_api as keystone
import horizon_hpe_storage.api.barbican_api as barbican

from openstack_dashboard.api import cinder

import logging

from collections import OrderedDict

LOG = logging.getLogger(__name__)


class IndexView(tabs.TabbedTableView):
    tab_group_class = storage_tabs.StorageTabs
    template_name = 'diags/index.html'


class DumpCinderView(forms.ModalFormView):
    form_class = diag_forms.DumpCinder
    modal_header = _("Diagnostic Test and Discovery Results")
    modal_id = "dump_cinder_modal"
    template_name = 'diags/dump_cinder.html'
    page_title = modal_header

    def get_initial(self):
        node_name = self.kwargs['node_name']
        return {'node_name': node_name}


class TestCinderView(forms.ModalFormView):
    form_class = diag_forms.TestCinder
    modal_header = _("Run Diagnostic Test")
    modal_id = "test_cinder_modal"
    template_name = 'diags/test_cinder.html'
    submit_label = _("Run Test")
    submit_url = "horizon:admin:hpe_storage:diags:test_cinder_node"
    success_url = reverse_lazy('horizon:admin:hpe_storage:index')
    page_title = _("Run Diagnostic Test")

    def get_context_data(self, **kwargs):
        context = super(TestCinderView, self).get_context_data(**kwargs)
        context["node_name"] = self.kwargs['node_name']
        args = (self.kwargs['node_name'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        node_name = self.kwargs['node_name']
        return {'node_name': node_name}


class TestAllCinderView(forms.ModalFormView):
    form_class = diag_forms.TestAllCinder
    modal_header = _("Run Diagnostic Test")
    modal_id = "test_all_cinder_modal"
    template_name = 'diags/test_all_cinder.html'
    submit_label = _("Run Diagnostic Tests")
    submit_url = reverse_lazy(
        "horizon:admin:hpe_storage:diags:test_all_cinder_nodes")
    success_url = reverse_lazy('horizon:admin:hpe_storage:index')
    page_title = _("Run Diagnostic Test")


class TestDetailView(tabs.TabView):
    tab_group_class = diags_tabs.TestDetailTabs
    template_name = 'horizon/common/_detail.html'
    page_title = "{{ test.test_name }}"
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def get_context_data(self, **kwargs):
        context = super(TestDetailView, self).get_context_data(**kwargs)
        test_results = self.get_data()
        context['test'] = test_results
        context['url'] = self.get_redirect_url()
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            node_info = self.kwargs['node_name'].split("::")
            node_name = node_info[0]
            node_type = node_info[1]

            self.keystone_api.do_setup(self.request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            node = self.barbican_api.get_node(node_name, node_type)

            # format data for panel
            test_results = {}
            test_results['test_name'] = node['node_name']
            test_results['run_time'] = node['diag_run_time']

            test_results['service_type'] = node_type

            test_results['host_ip'] = node['node_ip']
            test_results['ssh_name'] = node['ssh_name']

            test_results['config_path'] = "N/A"

            if node_type == self.barbican_api.CINDER_NODE_TYPE:
                test_results['config_path'] = node['config_path']

                config_status = node['diag_test_status']
                backend_sections = []
                storage_arrays = []
                self.backend_serial_numbers = []
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
                                if data:
                                    storage_arrays.append(data)
                            elif raw_result.startswith('config_items'):
                                item_str = raw_result[len('config_items:'):]
                                items = item_str.split(";;")
                                config_items = {}
                                for item in items:
                                    if "==" in item:
                                        key, value = item.split("==")
                                        if "password" in key:
                                            value = '*' * len(value)
                                        config_items[key] = value
                                disp_results['config_items'] = \
                                    OrderedDict(sorted(config_items.items()))
                            else:
                                if ":" in raw_result:
                                    key, value = raw_result.split(":")
                                    disp_results[key] = \
                                        self.color_result(value)

                        backend_sections.append(disp_results)

                test_results['config_test_results'] = backend_sections
                test_results['systems_info'] = storage_arrays

            software_status = node['software_test_status']
            node_groups = []
            sw_nodes = software_status.split("Software Test:")
            for sw_node in sw_nodes:
                if sw_node:
                    raw_results = sw_node.split("::")
                    disp_results = {}
                    for raw_result in raw_results:
                        if ":" in raw_result:
                            key, value = raw_result.split(":")
                            disp_results[key] = self.color_result(value)
                    node_groups.append(disp_results)

            test_results['software_test_results'] = node_groups

            test_results['raw_test_data'] = self.get_raw_data(node)
            # node['test_results'] = test_results

        except Exception as ex:
            redirect = self.get_redirect_url()
            exceptions.handle(self.request,
                              _('Unable to retrieve test details.'),
                              redirect=redirect)
        return test_results

    def color_result(self, value):
        fail_str = safestring.mark_safe('<font color="red">fail</font>')
        if value == "fail":
            return fail_str

        return value

    def get_backend_system_info(self, data):
        # pull all of the data out
        disp_results = {}
        items = data.split(";;")
        for item in items:
            key, value = item.split(":")
            if key == "licenses":
                licenses = value.split(";")
                disp_results[key] = licenses
            elif key == "serial_number":
                # don't display same system twice
                if value in self.backend_serial_numbers:
                    return None
                else:
                    disp_results[key] = value
                    self.backend_serial_numbers.append(value)
            else:
                disp_results[key] = value

        return disp_results

    def get_raw_data(self, node):
        stats = "node name: " + node['node_name'] + "\n"
        stats += "node type: " + node['node_type'] + "\n"
        stats += "ip: " + node['node_ip'] + "\n"
        stats += "SSH uname: " + node['ssh_name'] + "\n"
        stats += "SSH pwd: " + ('*' * len(node['ssh_pwd'])) + "\n"
        stats += "config path: " + node['config_path'] + "\n"
        stats += "run time: " + node['validation_time'] + "\n"

        diag_test = node['diag_test_status']
        backends = diag_test.split("Backend Section:")
        for backend in backends:
            if backend:
                stats += "\r\n"
                raw_results = backend.split("::")
                stats += "Driver Configuration Section [" + \
                         raw_results[0] + "]:\n"
                test_results = ""
                for raw_result in raw_results:
                    if raw_result.startswith('system_info'):
                        system_info = self.get_raw_backend_system_info(
                            raw_result[12:])
                    elif raw_result.startswith('config_items'):
                        config_items = ""
                        item_str = raw_result[len('config_items:'):]
                        items = item_str.split(";;")
                        for item in items:
                            if "==" in item:
                                key, value = item.split("==")
                                if "password" in key:
                                    value = '*' * len(value)
                                config_items += \
                                    ("\t\t" + key + ": " + value + "\n")
                    else:
                        if ":" in raw_result:
                            key, value = raw_result.split(":")
                            test_results += \
                                ("\t\t" + key + ": " + value + "\n")

                stats += "\n\tConfig Items ('cinder.conf'):\n" + config_items
                stats += "\n\tTest Results for 'cinder.conf':\n" + test_results
                stats += "\n\tSystem Information:\n" + system_info

        software_status = node['software_test_status']
        node_groups = []
        nodes = software_status.split("Software Test:")
        stats += "\nSoftware Test Results:\n"
        for node in nodes:
            if node:
                raw_results = node.split("::")
                for raw_result in raw_results:
                    if ":" in raw_result:
                        key, value = raw_result.split(":")
                        stats += ("\t" + key + ": " + value + "\n")

        return stats

    def get_raw_backend_system_info(self, data):
        # pull all of the data out
        disp_results = ""
        items = data.split(";;")
        license_str = "\t\tlicenses:\n\t\t\t"
        for item in items:
            key, value = item.split(":")
            if key == "licenses":
                licenses = value.split(";")
                license_str += ('\n\t\t\t'.join(licenses) + "\n")
            else:
                if key == "host_name":
                    host_name = value
                elif key == "cpgs":
                    cpgs = value
                elif key == "backend":
                    backend = value
                disp_results += ("\t\t" + key + ": " + value + "\n")

        # get pool info
        if host_name and cpgs:
            pool_name_start = host_name + '@' + backend + '#'
            pool_info = ""
            cur_cpgs = cpgs.split(',')
            pools = cinder.pool_list(self.request, detailed=True)
            for cpg in cur_cpgs:
                pool_name = pool_name_start + cpg
                for pool in pools:
                    if pool.name == pool_name:
                        pool_info += "\n\t\tScheduler Data for Pool: " + \
                                     pool_name + "\n"
                        pool_data = pool._apiresource._info['capabilities']
                        for key, value in pool_data.iteritems():
                            pool_info += ("\t\t\t" + key + ": " +
                                          str(value) + "\n")

        return disp_results + license_str + pool_info

    def get_redirect_url(self):
        return reverse('horizon:admin:hpe_storage:index')

    def get_tabs(self, request, *args, **kwargs):
        test = self.get_data()
        return self.tab_group_class(request, test=test, **kwargs)


class SWTestDetailView(tabs.TabView):
    tab_group_class = diags_tabs.SWTestDetailTabs
    template_name = 'horizon/common/_detail.html'
    page_title = "{{ test.test_name }}"
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def get_context_data(self, **kwargs):
        context = super(SWTestDetailView, self).get_context_data(**kwargs)
        test_results = self.get_data()
        context['test'] = test_results
        context['url'] = self.get_redirect_url()
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            node_info = self.kwargs['node_name'].split("::")
            node_name = node_info[0]
            node_type = node_info[1]

            self.keystone_api.do_setup(self.request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            node = self.barbican_api.get_node(node_name, node_type)

            # format data for panel
            test_results = {}
            test_results['test_name'] = node['node_name']
            test_results['run_time'] = node['diag_run_time']

            test_results['service_type'] = node_type

            test_results['host_ip'] = node['node_ip']
            test_results['ssh_name'] = node['ssh_name']

            test_results['config_path'] = "N/A"

            software_status = node['software_test_status']
            node_groups = []
            sw_nodes = software_status.split("Software Test:")
            for sw_node in sw_nodes:
                if sw_node:
                    raw_results = sw_node.split("::")
                    disp_results = {}
                    for raw_result in raw_results:
                        if ":" in raw_result:
                            key, value = raw_result.split(":")
                            disp_results[key] = self.color_result(value)
                    node_groups.append(disp_results)

            test_results['software_test_results'] = node_groups

        except Exception as ex:
            redirect = self.get_redirect_url()
            exceptions.handle(self.request,
                              _('Unable to retrieve test details.'),
                              redirect=redirect)
        return test_results

    def color_result(self, value):
        fail_str = safestring.mark_safe('<font color="red">fail</font>')
        if value == "fail":
            return fail_str

        return value

    def get_redirect_url(self):
        return reverse('horizon:admin:hpe_storage:index')

    def get_tabs(self, request, *args, **kwargs):
        test = self.get_data()
        return self.tab_group_class(request, test=test, **kwargs)


class TestNovaView(forms.ModalFormView):
    form_class = diag_forms.TestNova
    modal_header = _("Run Diagnostic Test")
    modal_id = "test_nova_modal"
    template_name = 'diags/test_nova.html'
    submit_label = _("Run Test")
    submit_url = "horizon:admin:hpe_storage:diags:test_nova_node"
    success_url = reverse_lazy('horizon:admin:hpe_storage:index')
    page_title = _("Run Diagnostic Test")

    def get_context_data(self, **kwargs):
        context = super(TestNovaView, self).get_context_data(**kwargs)
        context["node_name"] = self.kwargs['node_name']
        args = (self.kwargs['node_name'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        node_name = self.kwargs['node_name']
        return {'node_name': node_name}


class TestAllNovaView(forms.ModalFormView):
    form_class = diag_forms.TestAllNova
    modal_header = _("Run Diagnostic Test")
    modal_id = "test_all_nova_modal"
    template_name = 'diags/test_all_nova.html'
    submit_label = _("Run Diagnostic Tests")
    submit_url = reverse_lazy(
        "horizon:admin:hpe_storage:diags:test_all_nova_nodes")
    success_url = reverse_lazy('horizon:admin:hpe_storage:index')
    page_title = _("Run Diagnostic Test")


