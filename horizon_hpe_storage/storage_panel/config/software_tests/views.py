# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import tables

import horizon_hpe_storage.api.keystone_api as keystone
import horizon_hpe_storage.api.barbican_api as barbican

from horizon_hpe_storage.storage_panel.config.software_tests \
    import forms as sw_forms
from horizon_hpe_storage.storage_panel.config.software_tests \
    import tables as sw_tables


class SoftwareTestMixin(object):
    def get_context_data(self, **kwargs):
        context = super(SoftwareTestMixin, self).get_context_data(**kwargs)
        node_type = self.kwargs['node_type']
        context['node_type'] = node_type
        context['node_type_display'] = node_type.title()
        return context


class IndexView(SoftwareTestMixin, forms.ModalFormMixin, tables.DataTableView):
    table_class = sw_tables.SoftwareTestsTable
    template_name = 'config/software_tests/index.html'
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def get_data(self):
        try:
            node_type = self.kwargs['node_type']
            software_list = []
            self.keystone_api.do_setup(self.request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            software_list = self.barbican_api.get_software_tests(node_type)
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve softare list.'))
        return software_list


class CreateView(SoftwareTestMixin, forms.ModalFormView):
    form_class = sw_forms.AddSoftwareTest
    form_id = "sw_test_add_form"
    modal_header = _("Add Software Package for Cinder Node Test")
    modal_id = "sw_package_create_modal"
    submit_label = _("Add")
    submit_url = "horizon:admin:hpe_storage:config:software_tests:create"
    template_name = 'config/software_tests/create.html'
    success_url = 'horizon:admin:hpe_storage:config:software_tests:index'

    def get_initial(self):
        return {'node_type': self.kwargs['node_type']}

    def get_success_url(self):
        return reverse(self.success_url,
                       args=(self.kwargs['node_type'],))

    def get_context_data(self, **kwargs):
        context = super(CreateView, self).get_context_data(**kwargs)
        node_type = self.kwargs['node_type']
        args = (node_type,)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context


class EditView(SoftwareTestMixin, forms.ModalFormView):
    form_class = sw_forms.EditSoftwareTest
    form_id = "sw_test_edit_form"
    modal_header = _('Edit Software Package: %s')
    modal_id = "sw_test_edit_modal"
    submit_label = _("Save")
    submit_url = "horizon:admin:hpe_storage:config:software_tests:edit"
    template_name = 'config/software_tests/edit.html'
    success_url = 'horizon:admin:hpe_storage:config:software_tests:index'
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def get_success_url(self):
        return reverse(self.success_url,
                       args=(self.kwargs['node_type'],))

    def get_initial(self):
        node_type = self.kwargs['node_type']
        package = self.kwargs['package']
        min_version = None
        description = None
        try:
            self.keystone_api.do_setup(self.request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            tests = self.barbican_api.get_software_tests(node_type)
            for test in tests:
                if test['package'] == package:
                    min_version = test['min_version']
                    description = test['description']
                    break
        except Exception as ex:
            exceptions.handle(self.request,
                              _('Unable to retrieve software list.'))

        return {'node_type': node_type,
                'sw_package': package,
                'min_version': min_version,
                'description': description}

    def get_context_data(self, **kwargs):
        context = super(EditView, self).get_context_data(**kwargs)
        args = (self.kwargs['node_type'], self.kwargs['package'])
        context['submit_url'] = reverse(self.submit_url, args=args)
        context['modal_header'] = self.modal_header % self.kwargs['package']
        context['node_type'] = self.kwargs['node_type']
        context['package'] = self.kwargs['package']
        return context
