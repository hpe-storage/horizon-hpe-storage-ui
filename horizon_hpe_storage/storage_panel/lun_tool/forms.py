
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
from django.forms import ValidationError  # noqa
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages

import logging
import datetime
import json

LOG = logging.getLogger(__name__)

import horizon_hpe_storage.api.keystone_api as keystone
import horizon_hpe_storage.api.barbican_api as barbican
import horizon_hpe_storage.test_engine.node_test as tester
from horizon.utils import validators

from openstack_dashboard.api import cinder


class RunLunTool(forms.SelfHandlingForm):
    node_names = forms.CharField(
        max_length=500,
        label=_("Nova Nodes"),
        required=False,
        widget=forms.Textarea(
            attrs={'rows': 6, 'readonly': 'readonly'}))

    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()
    nodes = None

    def __init__(self, request, *args, **kwargs):
        super(forms.SelfHandlingForm, self).__init__(request, *args, **kwargs)
        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            self.nodes = self.barbican_api.get_all_nodes(
                barbican.NOVA_NODE_TYPE)

            names = ""
            for node in self.nodes:
                if names:
                    names += ", "
                names += node['node_name']

            names_field = self.fields['node_names']
            names_field.initial = names

        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to run volume path query.'),
                              redirect=redirect)

    def handle(self, request, data):
        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            self.nodes = self.barbican_api.get_all_nodes(
                barbican.NOVA_NODE_TYPE)

            # need list of all attached volumes
            volumes = cinder.volume_list(
                request,
                search_opts={'all_tenants': True})
            attached_vols = []
            vol_names = []
            for volume in volumes:
                # only process volumes that are attached
                if volume.attachments:
                    attached_vol_entry = {}
                    attached_vol_entry['vol_name'] = volume.name
                    attached_vol_entry['vol_id'] = volume.id
                    attached_vols.append(attached_vol_entry)
                    vol_names.append(volume.name)
            json_volume_names = json.dumps(vol_names)

            all_paths = []
            for node in self.nodes:
                # note 'section' must be lower case for diag tool
                credentials_data = {}
                credentials_data['section'] = \
                    node['node_name'].lower() + '-' + barbican.NOVA_NODE_TYPE
                credentials_data['service'] = barbican.NOVA_NODE_TYPE
                credentials_data['host_ip'] = node['node_ip']
                credentials_data['host_name'] = node['host_name']
                credentials_data['ssh_user'] = node['ssh_name']
                credentials_data['ssh_password'] = node['ssh_pwd']

                all_data = []
                all_data.append(credentials_data)
                json_conf_data = json.dumps(all_data)

                # first run ssh validation check on nova node
                node_test = tester.NodeTest()
                node_test.run_credentials_check_test(json_conf_data)

                if "fail" in node_test.test_result_text:
                    error_text = 'SSH credential validation failed'
                    LOG.info(("%s") % node_test.error_text)
                    continue

                # get the OpenStack vars to use
                if 'os_vars' in node:
                    os_vars = node['os_vars']
                else:
                    # use defaults
                    os_vars = self.barbican_api.get_lun_tool_default_os_vars()

                json_os_vars = json.dumps(os_vars)
                node_test.run_volume_paths_test(json_conf_data, json_os_vars,
                                                json_volume_names)

                LOG.info("Process lun tool results - start results")
                if node_test.test_result_text:
                    json_string = node_test.test_result_text
                    LOG.info("lun tool:json results - %s" % json_string)
                    parsed_json = json.loads(json_string)
                    LOG.info("lun tool:parsed_json results - %s" % parsed_json)

                path_data_for_node = []
                for entry in parsed_json:
                    path_entry = {}
                    path_entry['path'] = entry['Path']

                    vol_name = entry['Attached Volume']
                    item = [d for d in attached_vols
                            if d['vol_name'] == vol_name]
                    vol_id = None
                    if item:
                        vol_id = item[0]['vol_id']
                    path_entry['vol_name'] = vol_name
                    path_entry['vol_id'] = vol_id
                    path_data_for_node.append(path_entry)

                # store all the paths found for this nova node
                all_paths_entry = {}
                all_paths_entry['node_name'] = node['node_name']
                all_paths_entry['paths'] = path_data_for_node
                all_paths.append(all_paths_entry)

            cur_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.barbican_api.add_lun_tool_result(cur_time, all_paths)

            messages.success(
                request,
                _('Successfully ran volume path test'))
            return True

        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(
                request,
                _('Unable to run volume path: ') + ex.message,
                redirect=redirect)


class ManageOSVars(forms.SelfHandlingForm):
    os_username = forms.CharField(
        label=_("OS_USERNAME"))
    os_password = forms.RegexField(
        label=_("OS_PASSWORD"),
        widget=forms.PasswordInput(render_value=False),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    confirm_password = forms.CharField(
        label=_("Confirm OS_PASSWORD"),
        widget=forms.PasswordInput(render_value=False))
    os_tenant = forms.CharField(
        label=_("OS_TENANT_NAME"))
    os_auth = forms.CharField(
        label=_("OS_AUTH_URL"))

    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def __init__(self, request, *args, **kwargs):
        super(ManageOSVars, self).__init__(request, *args, **kwargs)

        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            os_vars = self.barbican_api.get_lun_tool_default_os_vars()

            if os_vars:
                self.fields['os_username'].initial = os_vars['os_username']
                self.fields['os_password'].initial = os_vars['os_password']
                self.fields['os_password'].widget.render_value = True
                self.fields['os_tenant'].initial = os_vars['os_tenant']
                self.fields['os_auth'].initial = os_vars['os_auth']

        except Exception as ex:
            exceptions.handle(request,
                              _("Unable to retrieve OpenStack Variables."))

    def clean(self):
        # Check to make sure password fields match
        form_data = super(ManageOSVars, self).clean()

        # ensure that data has changed
        os_username_field = self.fields['os_username']
        os_password_field = self.fields['os_password']
        os_tenant_field = self.fields['os_tenant']
        os_auth_field = self.fields['os_auth']

        if form_data['os_username'] == os_username_field.initial:
            if form_data['os_password'] == os_password_field.initial:
                if form_data['os_tenant'] == os_tenant_field.initial:
                    if form_data['os_auth'] == os_auth_field.initial:
                        raise forms.ValidationError(
                            _('No fields have been modified.'))

        # Check to make sure password fields match.
        if form_data['os_password'] != os_password_field.initial:
            if form_data['os_password'] != form_data['confirm_password']:
                raise ValidationError(_('Passwords do not match.'))

        return form_data

    def handle(self, request, data):
        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())

            os_vars = self.barbican_api.get_lun_tool_default_os_vars()
            self.barbican_api.delete_lun_tool_default_os_vars()

            self.barbican_api.add_lun_tool_default_os_vars(
                data['os_username'],
                data['os_password'],
                data['os_tenant'],
                data['os_auth']
            )

            messages.success(request, _('Successfully updated OpenStack '
                                        'environment variables'))
            return True
        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to update OpenStack '
                                'environment variables.'),
                              redirect=redirect)


class ShowDiff(forms.SelfHandlingForm):
    other_results = forms.ChoiceField(label=_("Compare against Query"),
                                      required=False)

    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()
    orig_result = None
    stored_results = None

    def __init__(self, request, *args, **kwargs):
        super(forms.SelfHandlingForm, self).__init__(request, *args, **kwargs)

        try:
            current_result_timestamp = kwargs['initial']['timestamp']

            # get list of available queries
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())

            self.stored_results = self.barbican_api.get_lun_tool_results()
            choices = []
            for result in self.stored_results:
                if result['timestamp'] == current_result_timestamp:
                    self.orig_result = result
                else:
                    choice = forms.ChoiceField = (result['timestamp'],
                                                  result['timestamp'])
                    choices.append(choice)

            self.fields['other_results'].choices = choices

        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to retrieve Volume Path '
                                'query results.'),
                              redirect=redirect)

    def handle(self, request, data):
        # base_timestamp = request.resolver_match.kwargs['timestamp']
        compare_timestamp = data['other_results']
        return compare_timestamp
