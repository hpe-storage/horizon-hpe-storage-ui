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

from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon.utils import memoized
from openstack_dashboard.api import cinder

from horizon_hpe_storage.storage_panel.diags import forms as diag_forms

from horizon import tabs
from openstack_dashboard.dashboards.admin.defaults import tabs as project_tabs

from horizon import tables
from horizon import tabs

import uuid
import base64
import re
from urlparse import urlparse

import horizon_hpe_storage.api.hp_ssmc_api as hpssmc
import horizon_hpe_storage.api.keystone_api as keystone
import horizon_hpe_storage.api.barbican_api as barbican

from horizon_hpe_storage.storage_panel import tabs as storage_tabs
from horizon_hpe_storage.storage_panel.diags import tabs as diags_tabs
from horizon_hpe_storage.storage_panel.diags import tables as diags_tables

from keystoneclient.v2_0 import client as keystone_client

import logging

LOG = logging.getLogger(__name__)


class IndexView(tabs.TabbedTableView):
    tab_group_class = storage_tabs.StorageTabs
    template_name = 'diags/index.html'
    page_title = _("HP Storage")


class DetailView(tabs.TabView):
    tab_group_class = diags_tabs.TestDetailTabs
    template_name = 'diags/detail.html'
    page_title = _("Test Details: {{ test.test_name }}")

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        test_results = self.get_data()
        table = diags_tables.DiagsTable(self.request)
        # context['test'] = test['test_results']
        context['test'] = test_results
        context['url'] = self.get_redirect_url()
        # context['actions'] = table.render_row_actions(test)
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            test_name = self.kwargs['test_name']
            keystone_api = keystone.KeystoneAPI()
            keystone_api.do_setup(self.request)
            barbican_api = barbican.BarbicanAPI()
            barbican_api.do_setup(None)

            test = barbican_api.get_diag_test(
                keystone_api.get_session_key(),
                'cinderdiags-' + test_name)

            # format data for panel
            test_results = {}
            test_results['test_name'] = test['test_name']
            test_results['run_time'] = test['run_time']

            if test['service_type'] == 'cinder':
                test_results['service_type'] = 'Cinder'
                test_results['config_path'] = test['config_path']
            elif test['service_type'] == 'nova':
                test_results['service_type'] = 'Nova'
                test_results['config_path'] = 'N/A'
            elif test['service_type'] == 'both':
                test_results['service_type'] = 'Cinder and Nova'
                test_results['config_path'] = test['config_path']
            else:
                test_results['service_type'] = 'Unknown'
                test_results['config_path'] = 'N/A'

            test_results['host_ip'] = test['host_ip']
            test_results['ssh_name'] = test['ssh_name']

            config_status = test['config_test_status']
            backend_sections = []
            backends = config_status.split("Backend Section:")
            for backend in backends:
                if backend:
                    raw_results = backend.split("::")
                    disp_results = {}
                    disp_results['backend_name'] = "[" + raw_results[0] + "]"
                    for raw_result in raw_results:
                        if ":" in raw_result:
                            key, value = raw_result.split(":")
                            disp_results[key] = value

                    backend_sections.append(disp_results)

            test_results['config_test_results'] = backend_sections

            software_status = test['software_test_status']
            node_groups = []
            nodes = software_status.split("Software Test:")
            for node in nodes:
                if node:
                    raw_results = node.split("::")
                    disp_results = {}
                    for raw_result in raw_results:
                        if ":" in raw_result:
                            key, value = raw_result.split(":")
                            disp_results[key] = value

                    node_groups.append(disp_results)

            test_results['software_test_results'] = node_groups
            test['test_results'] = test_results

        except Exception:
            redirect = self.get_redirect_url()
            exceptions.handle(self.request,
                              _('Unable to retrieve test details.'),
                              redirect=redirect)
        return test_results

    def get_redirect_url(self):
        return reverse('horizon:admin:hpe_storage:index')

    def get_tabs(self, request, *args, **kwargs):
        test = self.get_data()
        return self.tab_group_class(request, test=test, **kwargs)


class RunTestView(forms.ModalFormView):
    form_class = diag_forms.RunTest
    modal_header = _("Run Diagnostic Test")
    modal_id = "create_test_modal"
    template_name = 'diags/run_test.html'
    submit_label = _("Run Test")
    submit_url = "horizon:admin:hpe_storage:diags:run_test"
    success_url = reverse_lazy('horizon:admin:hpe_storage:index')
    page_title = _("Run Diagnostic Test")

    def get_context_data(self, **kwargs):
        context = super(RunTestView, self).get_context_data(**kwargs)
        context["test_name"] = self.kwargs['test_name']
        args = (self.kwargs['test_name'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    # @memoized.memoized_method
    # def get_data(self):
    #     try:
    #         test_name = self.kwargs['test_name']
    #         test = None # volume = cinder.volume_get(self.request, volume_id)
    #     except Exception:
    #         exceptions.handle(self.request,
    #                           _('Unable to retrieve diagnostic test details.'),
    #                           redirect=self.success_url)
    #     return test

    def get_initial(self):
        test_name = self.kwargs['test_name']
        return {'test_name': test_name}


class CreateTestView(forms.ModalFormView):
    form_class = diag_forms.CreateTest
    modal_header = _("Create Diagnostic Test")
    modal_id = "create_test_modal"
    template_name = 'diags/create_test.html'
    submit_label = _("Create Diagnostic Test")
    submit_url = reverse_lazy("horizon:admin:hpe_storage:diags:create_test")
    success_url = 'horizon:admin:hpe_storage:index'
    page_title = _("Create Diagnostic Test")

    def get_success_url(self):
        return reverse(self.success_url)


class EditTestView(forms.ModalFormView):
    form_class = diag_forms.EditTest
    modal_header = _("Edit Diagnostic Test")
    modal_id = "edit_test_modal"
    template_name = 'diags/edit_test.html'
    submit_label = _("Edit Diagnostic Test")
    submit_url = "horizon:admin:hpe_storage:diags:edit_test"
    success_url = reverse_lazy('horizon:admin:hpe_storage:diags:index')
    page_title = _("Edit Diagnostic Test")

    def get_context_data(self, **kwargs):
        context = super(EditTestView, self).get_context_data(**kwargs)
        args = (self.kwargs['test_name'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    @memoized.memoized_method
    def get_object(self, *args, **kwargs):
        test_name = self.kwargs['test_name']
        try:
            # keystone_api = keystone.KeystoneAPI()
            # keystone_api.do_setup(self.request)
            # barbican_api = barbican.BarbicanAPI()
            # barbican_api.do_setup(None)
            #
            # test = barbican_api.get_diag_test(keystone_api.get_session_key(), test_name)
            # return test
            i = 0
        except Exception as ex:
            msg = _('Unable to retrieve Diagnostic Test details.')
            exceptions.handle(self.request, msg)
        return self._object

    def get_initial(self):
        test_name = self.kwargs['test_name']
        return {'test_name': test_name}
