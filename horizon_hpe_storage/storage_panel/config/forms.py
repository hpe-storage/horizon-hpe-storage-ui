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
from django.forms import ValidationError  # noqa
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon.utils import validators

import logging

LOG = logging.getLogger(__name__)
import datetime
import json
from urlparse import urlparse

import horizon_hpe_storage.api.keystone_api as keystone
import horizon_hpe_storage.api.barbican_api as barbican
import horizon_hpe_storage.test_engine.node_test as tester

from openstack_dashboard.api import cinder as horizon_cinder


class CreateEndpoint(forms.SelfHandlingForm):
    backend = forms.ChoiceField(label=_("Available Cinder Backends"))
    endpoint_ip = forms.IPField(label=_("SSMC Instance Address"))
    endpoint_port = forms.IntegerField(
        label=_("SSMC Instance Port"),
        help_text=_("Enter an integer value between 1 and 65535."),
        validators=[validators.validate_port_range])
    uname = forms.CharField(max_length=255,
                            label=_("SSMC Username"))
    pwd = forms.RegexField(
        label=_("SSMC Password"),
        widget=forms.PasswordInput(render_value=False),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    confirm_password = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(render_value=False))

    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def __init__(self, request, *args, **kwargs):
        super(forms.SelfHandlingForm, self).__init__(request, *args, **kwargs)

        # get list of backend names from cinder
        self.keystone_api.do_setup(request)
        endpoints = self.keystone_api.get_ssmc_endpoints()

        pools = horizon_cinder.pool_list(self.request, detailed=True)
        backends = []
        for pool in pools:
            backends.append(pool.volume_backend_name)

        choices = []
        for backend in backends:
            # only show backends that haven't been assigned an endpoint
            matchFound = False
            for endpoint in endpoints:
                if endpoint['backend'] == backend:
                    matchFound = True
                    break
            if not matchFound:
                choice = forms.ChoiceField = (backend, backend)
                choices.append(choice)

        self.fields['backend'].choices = choices

        # set default port number
        self.fields['endpoint_port'].initial = '8443'

    def clean(self):
        # Check to make sure password fields match
        data = super(forms.Form, self).clean()
        if 'pwd' in data and 'confirm_password' in data:
            if data['pwd'] != data['confirm_password']:
                raise ValidationError(_('Passwords do not match.'))
        return data

    def handle(self, request, data):
        try:
            # create new keypoint service and endpoint
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            backend_name = 'ssmc-' + data['backend']
            port = str(data['endpoint_port'])
            endpoint = 'https://' + data['endpoint_ip'] + ':' + port + '/'
            self.keystone_api.add_ssmc_endpoint(backend_name, endpoint)

            # store credentials for endpoint using barbican
            self.barbican_api.add_ssmc_credentials(
                data['backend'],
                data['uname'],
                data['pwd'])

            messages.success(
                request,
                _('Successfully created SSMC Link for Cinder backend: %s') %
                data['backend'])
            return True
        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to create endpoint.'),
                              redirect=redirect)


class EditEndpoint(forms.SelfHandlingForm):
    backend = forms.CharField(label=_("Cinder Backend"),
                              required=False,
                              widget=forms.TextInput(
                                  attrs={'readonly': 'readonly'}))
    endpoint_ip = forms.IPField(label=_("SSMC Instance Address"))
    endpoint_port = forms.IntegerField(
        label=_("SSMC Instance Port"),
        help_text=_("Enter an integer value between 1 and 65535."),
        validators=[validators.validate_port_range])
    uname = forms.CharField(max_length=255,
                            label=_("SSMC Username"))
    pwd = forms.RegexField(
        label=_("SSMC Password"),
        widget=forms.PasswordInput(render_value=False),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    confirm_password = forms.CharField(
        label=_("Confirm Password"),
        required=False,
        widget=forms.PasswordInput(render_value=False))

    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def __init__(self, request, *args, **kwargs):
        super(EditEndpoint, self).__init__(request, *args, **kwargs)
        service_id = self.initial['service_id']

        backend_field = self.fields['backend']
        endpoint_ip_field = self.fields['endpoint_ip']
        endpoint_port_field = self.fields['endpoint_port']
        uname_field = self.fields['uname']
        pwd_field = self.fields['pwd']

        self.keystone_api.do_setup(request)
        self.barbican_api.do_setup(self.keystone_api.get_session())

        # initialize endpoint fields
        endpoint, name = self.keystone_api.get_ssmc_endpoint_for_service_id(
            service_id)
        backend_name = name[5:]    # remove 'ssmc-' prefix
        backend_field.initial = backend_name

        parsed = urlparse(endpoint['url'])
        endpoint_ip_field.initial = parsed.hostname
        endpoint_port_field.initial = parsed.port

        # initialize credentials fields
        uname, pwd = self.barbican_api.get_ssmc_credentials(backend_name)
        uname_field.initial = uname
        pwd_field.initial = pwd
        pwd_field.widget.render_value = True  # this makes it show up initially

        # save off current values

    def clean(self):
        form_data = self.cleaned_data

        # ensure that data has changed
        endpoint_ip_field = self.fields['endpoint_ip']
        endpoint_port_field = self.fields['endpoint_port']
        uname_field = self.fields['uname']
        pwd_field = self.fields['pwd']

        if form_data['endpoint_ip'] == endpoint_ip_field.initial:
            if form_data['endpoint_port'] == endpoint_port_field.initial:
                if form_data['uname'] == uname_field.initial:
                    if form_data['pwd'] == pwd_field.initial:
                        raise forms.ValidationError(
                            _('No fields have been modified.'))

        # Check to make sure password fields match.
        if form_data['pwd'] != pwd_field.initial:
            if form_data['pwd'] != form_data['confirm_password']:
                raise ValidationError(_('Passwords do not match.'))

        return form_data

    def handle(self, request, data):
        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())

            endpoint_ip_field = self.fields['endpoint_ip']
            endpoint_port_field = self.fields['endpoint_port']
            uname_field = self.fields['uname']
            pwd_field = self.fields['pwd']

            backend_name = 'ssmc-' + data['backend']

            # only update endpoint if url or port has changed
            new_endpoint_ip = data['endpoint_ip']
            new_endpoint_port = data['endpoint_port']
            if ((new_endpoint_ip != endpoint_ip_field.initial) or
                    (new_endpoint_port != endpoint_port_field.initial)):
                service_id = self.initial['service_id']
                port = str(new_endpoint_port)
                new_endpoint = 'https://' + \
                               data['endpoint_ip'] + \
                               ':' + port + '/'
                self.keystone_api.update_ssmc_endpoint_url(service_id,
                                                           new_endpoint)

            # only update credentials if they have changed
            new_uname = data['uname']
            new_pwd = data['pwd']
            host = data['backend']
            if new_uname == uname_field.initial:
                new_uname = None
            if new_pwd == pwd_field.initial:
                new_pwd = None

            if new_uname or new_pwd:
                # cached SSMC token is no longer valid
                cache.delete('ssmc-link-' + host)

                self.barbican_api.update_ssmc_credentials(
                    data['backend'],
                    new_uname,
                    new_pwd)

            messages.success(
                request,
                _('Successfully update SSMC Link for Cinder backend: %s') %
                data['backend'])
            return True
        except Exception:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to update endpoint.'),
                              redirect=redirect)


class LinkToSSMC(forms.SelfHandlingForm):
    name = forms.CharField(max_length=255, label=_("Volume"),
                           widget=forms.TextInput(
                               attrs={'readonly': 'readonly'}))

    def handle(self, request, data):
        try:
            link_url = self.initial['link_url']
            LOG.info(("## LAUNCH URL: %s") % link_url)
            # webbrowser.open(link_url)

            from django.http import HttpResponse
            response = HttpResponse("", status=302)
            response['Location'] = link_url
            HttpResponseRedirect(link_url)
            # return True
        except Exception:
            exceptions.handle(request,
                              _('Unable to link to SSMC.'))


def run_ssh_validation_test(node, node_type, barbican_api):
    credentials_data = {}
    all_data = []
    errors_occurred = False

    # note 'section' must be lower case for diag tool
    credentials_data['section'] = node['node_name'].lower() + '-' + node_type
    credentials_data['service'] = node_type
    credentials_data['host_ip'] = node['node_ip']
    credentials_data['ssh_user'] = node['ssh_name']
    credentials_data['ssh_password'] = node['ssh_pwd']

    all_data.append(credentials_data)
    json_test_data = json.dumps(all_data)

    # run ssh validation check on cinder node
    validator = tester.NodeTest()
    validator.run_credentials_check_test(json_test_data)

    if "fail" in validator.test_result_text:
        error_text = 'SSH credential validation failed'
        LOG.info(("%s") % validator.error_text)
        errors_occurred = True

    # update test data
    barbican_api.delete_node(
        node['node_name'],
        node_type)

    if errors_occurred:
        result = "Failed"
    else:
        result = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    config_path = None
    if node_type == barbican.CINDER_NODE_TYPE:
        config_path = node['config_path']

    barbican_api.add_node(
        node['node_name'],
        node_type,
        node['node_ip'],
        node['host_name'],
        node['ssh_name'],
        node['ssh_pwd'],
        config_path=config_path,
        ssh_validation_time=result)


class RegisterCinderNode(forms.SelfHandlingForm):
    node_name = forms.CharField(
        max_length=255,
        label=_("Name"),
        help_text=_("Assign a unique name to identify this Cinder node."))
    node_ip = forms.IPField(
        label=_("IP Address"),
        help_text=_("Address of system hosting the Cinder service."))
    host_name = forms.CharField(
        max_length=255,
        label=_("Host Name"),
        help_text=_("Host name associated with this IP address."))
    ssh_name = forms.CharField(
        max_length=255,
        label=_("SSH Username"),
        help_text=_("Username for SSH access to Cinder node."))
    ssh_pwd = forms.RegexField(
        label=_("SSH Password"),
        widget=forms.PasswordInput(render_value=False),
        help_text=_("Password for SSH access to Cinder node."),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    confirm_password = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(render_value=False))
    config_path = forms.CharField(
        label=_("Cinder config file path"),
        help_text=_("Path to cinder.conf file on the Cinder node."))

    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def __init__(self, request, *args, **kwargs):
        super(forms.SelfHandlingForm, self).__init__(request, *args, **kwargs)

        # populate path with a default value
        config_path_field = self.fields['config_path']
        config_path_field.initial = "/etc/cinder/cinder.conf"

    def clean(self):
        # Check to make sure password fields match
        data = super(forms.Form, self).clean()
        if 'ssh_pwd' in data and 'confirm_password' in data:
            if data['ssh_pwd'] != data['confirm_password']:
                raise ValidationError(_('Passwords do not match.'))

        data['service_type'] = barbican.CINDER_NODE_TYPE
        return data

    def handle(self, request, data):
        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            self.barbican_api.add_node(
                data['node_name'],
                barbican.CINDER_NODE_TYPE,
                data['node_ip'],
                data['host_name'],
                data['ssh_name'],
                data['ssh_pwd'],
                # data['test_replication'],
                config_path=data['config_path'])

            messages.success(request, _('Successfully registered Cinder '
                                        'node: %s') % data['node_name'])
            return True
        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to register Cinder node.'),
                              redirect=redirect)


class EditCinderNode(forms.SelfHandlingForm):
    node_name = forms.CharField(
        max_length=255,
        label=_("Name"),
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    node_ip = forms.IPField(
        label=_("IP Address"),
        help_text=_("Address of system hosting the Cinder service."))
    host_name = forms.CharField(
        max_length=255,
        label=_("Host Name"),
        help_text=_("Host name associated with this IP address."))
    ssh_name = forms.CharField(
        max_length=255,
        label=_("SSH Username"),
        help_text=_("Username for SSH access to the Cinder node."))
    ssh_pwd = forms.RegexField(
        label=_("SSH Password"),
        widget=forms.PasswordInput(render_value=False),
        help_text=_("Password for SSH access to the Cinder node."),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    confirm_password = forms.CharField(
        label=_("Confirm Password"),
        required=False,
        widget=forms.PasswordInput(render_value=False))
    config_path = forms.CharField(
        label=_("Cinder config file path"),
        help_text=_("Path to cinder.conf file on the Cinder node."))

    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def __init__(self, request, *args, **kwargs):
        super(EditCinderNode, self).__init__(request, *args, **kwargs)
        node_name = self.initial['node_name']

        try:
            node_name_field = self.fields['node_name']
            node_ip_field = self.fields['node_ip']
            host_name_field = self.fields['host_name']
            ssh_name_field = self.fields['ssh_name']
            ssh_pwd_field = self.fields['ssh_pwd']
            config_path_field = self.fields['config_path']
            # replication_field = self.fields['test_replication']

            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            node = self.barbican_api.get_node(
                node_name, barbican.CINDER_NODE_TYPE)

            node_name_field.initial = node['node_name']

            if 'node_ip' in node:
                node_ip_field.initial = node['node_ip']
            else:
                node_ip_field.initial = ''

            if 'host_name' in node:
                host_name_field.initial = node['host_name']
            else:
                host_name_field.initial = ''

            if 'ssh_name' in node:
                ssh_name_field.initial = node['ssh_name']
            else:
                ssh_name_field.initial = ''

            if 'ssh_pwd' in node:
                ssh_pwd_field.initial = node['ssh_pwd']
            else:
                ssh_pwd_field.initial = ''

            # this makes it show up initially
            ssh_pwd_field.widget.render_value = True

            if 'config_path' in node:
                config_path_field.initial = node['config_path']
            else:
                config_path_field.initial = ''

            # if 'test_replication' in node:
            #     replication_field.initial = node['test_replication']
            # else:
            #     replication_field.initial = ''

        except Exception as ex:
            msg = _('Unable to retrieve Cinder Node details.')
            exceptions.handle(self.request, msg)

    def clean(self):
        form_data = self.cleaned_data

        # ensure that data has changed
        node_ip_field = self.fields['node_ip']
        host_name_field = self.fields['host_name']
        ssh_name_field = self.fields['ssh_name']
        ssh_pwd_field = self.fields['ssh_pwd']
        config_path_field = self.fields['config_path']
        # replication_field = self.fields['test_replication']

        if form_data['node_ip'] == \
                node_ip_field.initial:
            if form_data['host_name'] == \
                    host_name_field.initial:
                if form_data['ssh_name'] == \
                        ssh_name_field.initial:
                    if form_data['ssh_pwd'] == \
                            ssh_pwd_field.initial:
                        if form_data['config_path'] == \
                                config_path_field.initial:
                            # if form_data['test_replication'] == \
                            #         replication_field.initial:
                                raise forms.ValidationError(
                                    _('No fields have been modified.'))

        # Check to make sure password fields match.
        if form_data['ssh_pwd'] != ssh_pwd_field.initial:
            if form_data['ssh_pwd'] != form_data['confirm_password']:
                raise ValidationError(_('Passwords do not match.'))

        form_data['service_type'] = barbican.CINDER_NODE_TYPE
        return form_data

    def handle(self, request, data):
        try:
            # no barbican api for update, so delete and add
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            self.barbican_api.delete_node(
                self.fields['node_name'].initial,
                barbican.CINDER_NODE_TYPE)

            self.barbican_api.add_node(
                data['node_name'],
                barbican.CINDER_NODE_TYPE,
                data['node_ip'],
                data['host_name'],
                data['ssh_name'],
                data['ssh_pwd'],
                # data['test_replication'],
                config_path=data['config_path'])

            messages.success(
                request,
                _('Successfully updated Cinder node registration'))
            return True
        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to update Cinder node registration'),
                              redirect=redirect)


class ValidateCinderNode(forms.SelfHandlingForm):
    node_name = forms.CharField(
        max_length=255,
        label=_("Cinder Node"),
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def __init__(self, request, *args, **kwargs):
        super(forms.SelfHandlingForm, self).__init__(request, *args, **kwargs)
        node_name = self.initial['node_name']
        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            self.node = self.barbican_api.get_node(
                node_name,
                barbican.CINDER_NODE_TYPE)

        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to run validate credentials test.'),
                              redirect=redirect)

    def handle(self, request, data):
        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            run_ssh_validation_test(self.node,
                                    barbican.CINDER_NODE_TYPE,
                                    self.barbican_api)
            messages.success(request, _('SSH credentials test completed'))
            return True
        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to run SSH credentials test: ') +
                              ex.message, redirect=redirect)


class ValidateAllCinderNodes(forms.SelfHandlingForm):
    node_names = forms.CharField(
        max_length=500,
        label=_("Cinder Nodes"),
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
                barbican.CINDER_NODE_TYPE)

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
                              _('Unable to run validate credentials test.'),
                              redirect=redirect)

    def handle(self, request, data):
        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())

            for node in self.nodes:
                run_ssh_validation_test(node,
                                        barbican.CINDER_NODE_TYPE,
                                        self.barbican_api)

            messages.success(request, _('All SSH credential tests completed'))
            return True
        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to run SSH credentials test: ') +
                              ex.message, redirect=redirect)


class RegisterNovaNode(forms.SelfHandlingForm):
    node_name = forms.CharField(
        max_length=255,
        label=_("Name"),
        help_text=_("Assign a unique name to identify this Nova node."))
    node_ip = forms.IPField(
        label=_("IP Address"),
        help_text=_("Address of system hosting the Nova service."))
    host_name = forms.CharField(
        max_length=255,
        label=_("Host Name"),
        help_text=_("Host name associated with this IP address."))
    ssh_name = forms.CharField(
        max_length=255,
        label=_("SSH Username"),
        help_text=_("Username for SSH access to Nova node."))
    ssh_pwd = forms.RegexField(
        label=_("SSH Password"),
        widget=forms.PasswordInput(render_value=False),
        help_text=_("Password for SSH access to Nova node."),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    confirm_password = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(render_value=False))

    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def __init__(self, request, *args, **kwargs):
        super(forms.SelfHandlingForm, self).__init__(request, *args, **kwargs)

    def clean(self):
        # Check to make sure password fields match
        data = super(forms.Form, self).clean()
        if 'ssh_pwd' in data and 'confirm_password' in data:
            if data['ssh_pwd'] != data['confirm_password']:
                raise ValidationError(_('Passwords do not match.'))

        data['service_type'] = barbican.NOVA_NODE_TYPE
        return data

    def handle(self, request, data):
        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            self.barbican_api.add_node(
                data['node_name'],
                barbican.NOVA_NODE_TYPE,
                data['node_ip'],
                data['host_name'],
                data['ssh_name'],
                data['ssh_pwd'])

            messages.success(request, _('Successfully registered Nova '
                                        'node: %s') % data['node_name'])
            return True
        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to register Nova node.'),
                              redirect=redirect)


class EditNovaNode(forms.SelfHandlingForm):
    node_name = forms.CharField(
        max_length=255,
        label=_("Node Name"),
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    node_ip = forms.IPField(
        label=_("IP Address"),
        help_text=_("Address of system hosting the Nova service."))
    host_name = forms.CharField(
        max_length=255,
        label=_("Host Name"),
        help_text=_("Host name associated with this IP address."))
    ssh_name = forms.CharField(
        max_length=255,
        label=_("SSH Username"),
        help_text=_("Username for SSH access to the Nova node."))
    ssh_pwd = forms.RegexField(
        label=_("SSH Password"),
        widget=forms.PasswordInput(render_value=False),
        help_text=_("Password for SSH access to the Nova node."),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    confirm_password = forms.CharField(
        label=_("Confirm Password"),
        required=False,
        widget=forms.PasswordInput(render_value=False))

    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def __init__(self, request, *args, **kwargs):
        super(EditNovaNode, self).__init__(request, *args, **kwargs)
        node_name = self.initial['node_name']

        try:
            node_name_field = self.fields['node_name']
            node_ip_field = self.fields['node_ip']
            host_name_field = self.fields['host_name']
            ssh_name_field = self.fields['ssh_name']
            ssh_pwd_field = self.fields['ssh_pwd']

            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            node = self.barbican_api.get_node(
                node_name, barbican.NOVA_NODE_TYPE)

            node_name_field.initial = node['node_name']

            if 'node_ip' in node:
                node_ip_field.initial = node['node_ip']
            else:
                node_ip_field.initial = ''

            if 'host_name' in node:
                host_name_field.initial = node['host_name']
            else:
                host_name_field.initial = ''

            if 'ssh_name' in node:
                ssh_name_field.initial = node['ssh_name']
            else:
                ssh_name_field.initial = ''

            if 'ssh_pwd' in node:
                ssh_pwd_field.initial = node['ssh_pwd']
            else:
                ssh_pwd_field.initial = ''

            # this makes it show up initially
            ssh_pwd_field.widget.render_value = True

        except Exception as ex:
            msg = _('Unable to retrieve Nova Node details.')
            exceptions.handle(self.request, msg)

    def clean(self):
        form_data = self.cleaned_data

        # ensure that data has changed
        node_ip_field = self.fields['node_ip']
        host_name_field = self.fields['host_name']
        ssh_name_field = self.fields['ssh_name']
        ssh_pwd_field = self.fields['ssh_pwd']

        if form_data['node_ip'] == node_ip_field.initial:
            if form_data['host_name'] == host_name_field.initial:
                if form_data['ssh_name'] == ssh_name_field.initial:
                    if form_data['ssh_pwd'] == ssh_pwd_field.initial:
                        raise forms.ValidationError(
                            _('No fields have been modified.'))

        # Check to make sure password fields match.
        if form_data['ssh_pwd'] != ssh_pwd_field.initial:
            if form_data['ssh_pwd'] != form_data['confirm_password']:
                raise ValidationError(_('Passwords do not match.'))

        form_data['service_type'] = barbican.NOVA_NODE_TYPE
        return form_data

    def handle(self, request, data):
        try:
            # no barbican api for update, so delete and add
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            self.barbican_api.delete_node(
                self.fields['node_name'].initial,
                barbican.NOVA_NODE_TYPE)

            self.barbican_api.add_node(
                data['node_name'],
                barbican.NOVA_NODE_TYPE,
                data['node_ip'],
                data['host_name'],
                data['ssh_name'],
                data['ssh_pwd'])

            messages.success(
                request,
                _('Successfully updated Nova node registration'))
            return True
        except Exception:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to update Nova node registration'),
                              redirect=redirect)


class ValidateNovaNode(forms.SelfHandlingForm):
    node_name = forms.CharField(
        max_length=255,
        label=_("Nova Node"),
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()
    node = None

    def __init__(self, request, *args, **kwargs):
        super(forms.SelfHandlingForm, self).__init__(request, *args, **kwargs)
        node_name = self.initial['node_name']
        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            self.node = self.barbican_api.get_node(
                node_name,
                barbican.NOVA_NODE_TYPE)

        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to run validate credentials test.'),
                              redirect=redirect)

    def handle(self, request, data):
        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            run_ssh_validation_test(self.node,
                                    barbican.NOVA_NODE_TYPE,
                                    self.barbican_api)
            messages.success(request, _('SSH credentials test completed'))
            return True
        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to run SSH credentials test: ') +
                              ex.message, redirect=redirect)


class ValidateAllNovaNodes(forms.SelfHandlingForm):
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
                              _('Unable to run validate credentials test.'),
                              redirect=redirect)

    def handle(self, request, data):
        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())

            for node in self.nodes:
                run_ssh_validation_test(node,
                                        barbican.NOVA_NODE_TYPE,
                                        self.barbican_api)

            messages.success(request, _('All SSH credential tests completed'))
            return True
        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to run SSH credentials test: ') +
                              ex.message, redirect=redirect)


class ManageOSVars(forms.SelfHandlingForm):
    node_name = forms.CharField(
        max_length=255,
        label=_("Node Name"),
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))
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
        node_name = self.initial['node_name']

        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            nova_node = self.barbican_api.get_node(
                node_name,
                barbican.NOVA_NODE_TYPE)

            if nova_node:
                if 'os_vars' in nova_node:
                    os_vars = nova_node['os_vars']
                    self.fields['os_username'].initial = os_vars['os_username']
                    self.fields['os_password'].initial = os_vars['os_password']
                    self.fields['os_password'].widget.render_value = True
                    self.fields['os_tenant'].initial = os_vars['os_tenant']
                    self.fields['os_auth'].initial = os_vars['os_auth']

        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to update Nova node registration'),
                              redirect=redirect)

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
            node_name = self.fields['node_name'].initial
            node = self.barbican_api.get_node(
                node_name,
                barbican.NOVA_NODE_TYPE)

            self.barbican_api.delete_node(
                self.fields['node_name'].initial,
                barbican.NOVA_NODE_TYPE)

            diag_run_time = None
            if 'diag_run_time' in node:
                diag_run_time = node['diag_run_time']

            diag_test_status = None
            if 'diag_test_status' in node:
                diag_test_status = node['diag_test_status']

            ssh_validation_time = None
            if 'validation_time' in node:
                ssh_validation_time = node['validation_time']

            software_status = None
            if 'software_test_status' in node:
                software_status = node['software_test_status']

            os_vars = {'os_username': data['os_username'],
                       'os_password': data['os_password'],
                       'os_tenant': data['os_tenant'],
                       'os_auth': data['os_auth']}

            self.barbican_api.add_node(
                node_name,
                barbican.NOVA_NODE_TYPE,
                node['node_ip'],
                node['host_name'],
                node['ssh_name'],
                node['ssh_pwd'],
                diag_status=diag_test_status,
                software_status=software_status,
                diag_run_time=diag_run_time,
                ssh_validation_time=ssh_validation_time,
                os_vars=os_vars)

            messages.success(request, _('Successfully updated OpenStack '
                                        'environment variables'))
            return True
        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to update OpenStack environment '
                                'variables.'),
                              redirect=redirect)
