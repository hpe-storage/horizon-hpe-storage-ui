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
from django.template import defaultfilters as filters
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import forms
from horizon import tables

from openstack_dashboard import api
from openstack_dashboard import policy

import horizon_hpe_storage.api.keystone_api as keystone
import horizon_hpe_storage.api.barbican_api as barbican


class CreateTestAction(tables.LinkAction):
    name = "create_test"
    verbose_name = _("Create Diagnostic Test")
    url = "horizon:admin:hpe_storage:diags:create_test"
    classes = ("ajax-modal",)
    icon = "plus"


class DeleteTestAction(tables.DeleteAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Diagnostic Test",
            u"Delete Diagnostic Tests",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Diagnostic Test",
            u"Deleted Diagnostic Tests",
            count
        )

    def delete(self, request, obj_id):
        keystone_api = keystone.KeystoneAPI()
        keystone_api.do_setup(request)
        barbican_api = barbican.BarbicanAPI()
        barbican_api.do_setup(None)
        barbican_api.delete_diag_test(keystone_api.get_session_key(), obj_id)


class RunTestAction(tables.LinkAction):
    name = "run_test"
    verbose_name = _("Run Diagnostic Test")
    url = "horizon:admin:hpe_storage:diags:run_test"
    classes = ("ajax-modal",)


class EditTestAction(tables.LinkAction):
    name = "edit_test"
    verbose_name = _("Edit Diagnostic Test")
    url = "horizon:admin:hpe_storage:diags:edit_test"
    classes = ("ajax-modal",)


def render_service_type(test):
    if test['service_type'] == 'cinder':
        type = "Cinder"
    elif test['service_type'] == 'nova':
        type = "Nova"
    elif test['service_type'] == 'both':
        type = "Cinder and Nova"
    return type


class DiagsTable(tables.DataTable):
    test_name = tables.Column(
        'test_name',
        verbose_name=_('Test Name'),
        form_field=forms.CharField(max_length=64),
        link="horizon:admin:hpe_storage:diags:detail")
    service_type = tables.Column(
        render_service_type,
        verbose_name=_('Service Type'),
        form_field=forms.CharField(max_length=64))
    host_ip = tables.Column(
        'host_ip',
        verbose_name=_('Host IP'),
        form_field=forms.CharField(max_length=64))
    ssh_user = tables.Column(
        'ssh_name',
        verbose_name=_('SSH Username'),
        form_field=forms.CharField(max_length=64))
    conf_file_path = tables.Column(
        'config_path',
        verbose_name=_('Config File Path'),
        form_field=forms.CharField(max_length=64))
    last_run = tables.Column(
        'run_time',
        verbose_name=_('Last Successful Run'),
        form_field=forms.CharField(max_length=64))

    def get_object_id(self, test):
        return test['test_name']

    class Meta(object):
        name = "diags"
        verbose_name = _("Cinder Diagnostics")
        # hidden_title = False
        table_actions = (CreateTestAction, DeleteTestAction,)
        row_actions = (RunTestAction, EditTestAction, DeleteTestAction,)
