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
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon.utils import validators

import logging
from subprocess import Popen, PIPE
from threading import Thread
from Queue import Queue, Empty

LOG = logging.getLogger(__name__)
import datetime
import json

import horizon_hpe_storage.api.keystone_api as keystone
import horizon_hpe_storage.api.barbican_api as barbican

SERVICE_TYPES = (
    ("cinder", _("Cinder")),
    ("nova", _("Nova")),
    ("both", _("Cinder and Nova")),
)


class CreateTest(forms.SelfHandlingForm):
    test_name = forms.CharField(
        max_length=255,
        label=_("Test Name"))
    service_type = forms.ChoiceField(
        label=_("Service Type"),
        help_text=_("The service type to test on the host."),
        widget=forms.Select(
            attrs={'class': 'switchable', 'data-slug': 'source'}))
    host_ip = forms.IPField(
        label=_("Host IP"),
        help_text=_("Address of system hosting the Cinder or Nova service."))
    ssh_name = forms.CharField(
        max_length=255,
        label=_("SSH Username"),
        help_text=_("Username for SSH access to Cinder or Nova service host."))
    ssh_pwd = forms.RegexField(
        label=_("SSH Password"),
        widget=forms.PasswordInput(render_value=False),
        help_text=_("Password for SSH access to Cinder or Nova service host."),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    confirm_password = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(render_value=False))
    config_path = forms.CharField(
        label=_("Cinder config file path"),
        help_text=_("Path to cinder.conf file on Cinder service host."),
        required=False,
        widget=forms.widgets.TextInput(
            attrs={'class': 'switched', 'data-switch-on': 'source',
                   'data-source-both': _('Cinder config file path'),
                   'data-source-cinder': _('Cinder config file path'),
                   }))


    def __init__(self, request, *args, **kwargs):
        super(forms.SelfHandlingForm, self).__init__(request, *args, **kwargs)

        self.fields['service_type'].choices = SERVICE_TYPES

    def clean(self):
        # Check to make sure password fields match
        data = super(forms.Form, self).clean()
        if 'ssh_pwd' in data and 'confirm_password' in data:
            if data['ssh_pwd'] != data['confirm_password']:
                raise ValidationError(_('Passwords do not match.'))

        if data['service_type'] == "nova":
            data['config_path'] = "N/A"
        elif 'config_path' not in data:
            msg = _('This field is required')
            self._errors['config_path'] = self.error_class([msg])

        return data

    def handle(self, request, data):
        try:
            # get keystone session key for barbican
            keystone_api = keystone.KeystoneAPI()
            keystone_api.do_setup(self.request)

            # store credentials for endpoint using barbican
            barbican_api = barbican.BarbicanAPI()
            barbican_api.do_setup(None)
            barbican_api.add_diag_test(keystone_api.get_session_key(),
                                       data['test_name'],
                                       data['service_type'],
                                       data['host_ip'],
                                       data['ssh_name'],
                                       data['ssh_pwd'],
                                       data['config_path'])

            messages.success(request, _('Successfully created diagnostic '
                                        'test: %s') % data['test_name'])
            return True
        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to create diagnostic test.'),
                              redirect=redirect)


class EditTest(forms.SelfHandlingForm):
    test_name = forms.CharField(
        max_length=255,
        label=_("Test Name"),
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    service_type = forms.ChoiceField(
        label=_("Service Type"),
        help_text=_("The service type to test on the host."),
        widget=forms.Select(
            attrs={'class': 'switchable', 'data-slug': 'source'}))
    host_ip = forms.IPField(
        label=_("Host IP"),
        help_text=_("Address of system hosting the Cinder or Nova service."))
    ssh_name = forms.CharField(
        max_length=255,
        label=_("SSH Username"),
        help_text=_("Username for SSH access to Cinder or Nova service host."))
    ssh_pwd = forms.RegexField(
        label=_("SSH Password"),
        widget=forms.PasswordInput(render_value=False),
        help_text=_("Password for SSH access to Cinder or Nova service host."),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    confirm_password = forms.CharField(
        label=_("Confirm Password"),
        required=False,
        widget=forms.PasswordInput(render_value=False))
    config_path = forms.CharField(
        label=_("Cinder config file path"),
        help_text=_("Path to cinder.conf file on Cinder service host."),
        required=False,
        widget=forms.widgets.TextInput(
            attrs={'class': 'switched', 'data-switch-on': 'source',
                   'data-source-both': _('Cinder config file path'),
                   'data-source-cinder': _('Cinder config file path'),
                   }))

    keystone_api = None
    barbican_api = None

    def __init__(self, request, *args, **kwargs):
        super(EditTest, self).__init__(request, *args, **kwargs)
        test_name = self.initial['test_name']
        self.fields['service_type'].choices = SERVICE_TYPES

        try:
            test_name_field = self.fields['test_name']
            host_ip_field = self.fields['host_ip']
            ssh_name_field = self.fields['ssh_name']
            ssh_pwd_field = self.fields['ssh_pwd']
            config_path_field = self.fields['config_path']

            self.keystone_api = keystone.KeystoneAPI()
            self.keystone_api.do_setup(self.request)
            self.barbican_api = barbican.BarbicanAPI()
            self.barbican_api.do_setup(None)

            test = self.barbican_api.get_diag_test(
                self.keystone_api.get_session_key(),
                'cinderdiags-' + test_name)

            test_name_field.initial = test['test_name']

            current_service_type = test['service_type']
            self.initial['service_type'] = current_service_type

            host_ip_field.initial = test['host_ip']
            ssh_name_field.initial = test['ssh_name']
            ssh_pwd_field.initial = test['ssh_pwd']
            ssh_pwd_field.widget.render_value = True  # this makes it show up initially

            config_path_field.initial = test['config_path']

        except Exception as ex:
            msg = _('Unable to retrieve Diagnostic Test details.')
            exceptions.handle(self.request, msg)

    def clean(self):
        form_data = self.cleaned_data

        # ensure that data has changed
        service_type_field = self.fields['service_type']
        host_ip_field = self.fields['host_ip']
        ssh_name_field = self.fields['ssh_name']
        ssh_pwd_field = self.fields['ssh_pwd']
        config_path_field = self.fields['config_path']

        if form_data['service_type'] == service_type_field.initial:
            if form_data['host_ip'] == host_ip_field.initial:
                if form_data['ssh_name'] == ssh_name_field.initial:
                    if form_data['ssh_pwd'] == ssh_pwd_field.initial:
                        if form_data['config_path'] == config_path_field.initial:
                            raise forms.ValidationError(
                                _('No fields have been modified.'))

        # Check to make sure password fields match.
        if form_data['ssh_pwd'] != ssh_pwd_field.initial:
            if form_data['ssh_pwd'] != form_data['confirm_password']:
                raise ValidationError(_('Passwords do not match.'))

        if form_data['service_type'] == "nova":
            form_data['config_path'] = "N/A"
        elif 'config_path' not in form_data:
            msg = _('This field is required')
            self._errors['config_path'] = self.error_class([msg])

        return form_data

    def handle(self, request, data):
        try:
            # no barbican api for update, so delete and add
            self.barbican_api.delete_diag_test(self.keystone_api.get_session_key(),
                                               self.fields['test_name'].initial)

            self.barbican_api.add_diag_test(self.keystone_api.get_session_key(),
                                            data['test_name'],
                                            data['service_type'],
                                            data['host_ip'],
                                            data['ssh_name'],
                                            data['ssh_pwd'],
                                            data['config_path'])

            messages.success(request, _('Successfully updated Diagnostic Test'))
            return True
        except Exception:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to update diagnostic test'),
                              redirect=redirect)


class RunTest(forms.SelfHandlingForm):
    test_name = forms.CharField(
        max_length=255,
        label=_("Test Name"),
        required=False,
        widget=forms.TextInput(
        attrs={'readonly': 'readonly'}))

    keystone_api = None
    barbican_api = None
    test = None
    io_q = None
    proc = None
    errors_occurred = False
    error_text = ''
    test_result_text = ''
    options_test_results = None
    software_test_results = None
    stream_open = True

    def __init__(self, request, *args, **kwargs):
        super(RunTest, self).__init__(request, *args, **kwargs)
        test_name = self.initial['test_name']
        try:
            self.keystone_api = keystone.KeystoneAPI()
            self.keystone_api.do_setup(self.request)
            self.barbican_api = barbican.BarbicanAPI()
            self.barbican_api.do_setup(None)

            self.test = self.barbican_api.get_diag_test(
                self.keystone_api.get_session_key(),
                'cinderdiags-' + test_name)

        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to run diagnostic test.'),
                              redirect=redirect)

    def stream_watcher(self, identifier, stream):
        for line in stream:
            # block for 1 sec
            self.io_q.put((identifier, line))

        if not stream.closed:
            self.stream_open = False
            stream.close()

    def printer(self):
        while True:
            try:
                item = self.io_q.get(True, 1)
            except Empty:
                # no output in either stream for 1 sec so check if we are done
                if self.proc.poll() is not None:
                    break
            else:
                identifier, line = item
                if identifier is 'STDERR':
                    test_line = line.lower()
                    if 'failed' in test_line or 'error' in test_line:
                        self.errors_occurred = True
                        self.error_text += line
                else:
                    self.test_result_text += line

                LOG.info(("%s:%s") % (identifier, line))

    def run_options_check_test(self, test_data):
        self.io_q = Queue()
        self.proc = Popen(['cinderdiags', '-v', 'options-check', '-f', 'json',
                           '-conf-data', test_data],
                          stdout=PIPE,
                          stderr=PIPE)
        Thread(target=self.stream_watcher, name='stdout-watcher',
               args=('STDOUT', self.proc.stdout)).start()
        Thread(target=self.stream_watcher, name='stderr-watcher',
               args=('STDERR', self.proc.stderr)).start()
        Thread(target=self.printer, name='printer').start()

        import time
        done = False
        while not done:
            time.sleep(1)
            if self.proc.stdout.closed:
                done = True

    def run_software_check_test(self, test_data):
        self.io_q = Queue()
        self.proc = Popen(['cinderdiags', '-v', 'software-check', '-f', 'json',
                           '-conf-data', test_data],
                          stdout=PIPE,
                          stderr=PIPE)
        Thread(target=self.stream_watcher, name='stdout-watcher',
               args=('STDOUT', self.proc.stdout)).start()
        Thread(target=self.stream_watcher, name='stderr-watcher',
               args=('STDERR', self.proc.stderr)).start()
        Thread(target=self.printer, name='printer').start()

        import time
        done = False
        while not done:
            time.sleep(1)
            if self.proc.stdout.closed:
                done = True

    def clean(self):
        # validate test params needed to run test
        data = super(forms.Form, self).clean()

        cinder_data = {}
        nova_data = {}
        all_data = []

        test_type = self.test['service_type']
        if test_type == 'cinder' or test_type == 'both':
            cinder_data['section'] = self.test['test_name'] + '-cinder'
            cinder_data['service'] = 'cinder'
            cinder_data['host_ip'] = self.test['host_ip']
            cinder_data['ssh_user'] = self.test['ssh_name']
            cinder_data['ssh_password'] = self.test['ssh_pwd']
            cinder_data['conf_source'] = self.test['config_path']

            all_data.append(cinder_data)
            json_test_data = json.dumps(all_data)

            # run options-check for cinder node test
            self.run_options_check_test(json_test_data)
            self.options_test_results = self.test_result_text

            if self.errors_occurred:
                LOG.info(("%s") % self.error_text)
                # use better error messages
                error_type_found = False
                error_text = 'Test could not be completed due to the following issue(s):'
                if "invalid ssh" in self.error_text.lower():
                    error_text += ('<li>' + "Invalid SSH credentials" + '</li>')
                    error_type_found = True
                if "unable to connect" in self.error_text.lower():
                    error_text += ('<li>' + "Unable to connect to host: " +
                                   cinder_data['host_ip'] + '</li>')
                    error_type_found = True
                if "unable to copy" in self.error_text.lower():
                    error_text += ('<li>' + "Host Cinder config file path not found: " +
                                   '</li>' +
                                   '<li>' + cinder_data['conf_source'] + '</li>')
                    error_type_found = True
                if not error_type_found:
                    error_text += ('<li>' + "Check Horizon logs for more details" + '</li>')

                # use HTML markup for better formatted text
                status = mark_safe(error_text)
                raise ValidationError(status)

        if test_type == 'nova' or test_type == 'both':
            nova_data['section'] = self.test['test_name'] + '-nova'
            nova_data['service'] = 'nova'
            nova_data['host_ip'] = self.test['host_ip']
            nova_data['ssh_user'] = self.test['ssh_name']
            nova_data['ssh_password'] = self.test['ssh_pwd']

            all_data.append(nova_data)

            json_test_data = json.dumps(all_data)

            self.test_result_text = ''
            self.run_software_check_test(json_test_data)
            self.software_test_results = self.test_result_text

            if self.errors_occurred:
                LOG.info(("%s") % self.error_text)
                # use better error messages
                error_type_found = False
                error_text = 'Test could not be completed due to the following issue(s):'
                if "invalid ssh" in self.error_text.lower():
                    error_text += ('<li>' + "Invalid SSH credentials" + '</li>')
                    error_type_found = True
                if "unable to connect" in self.error_text.lower():
                    error_text += ('<li>' + "Unable to connect to host: " +
                                   nova_data['host_ip'] + '</li>')
                    error_type_found = True
                if "unable to copy" in self.error_text.lower():
                    error_text += ('<li>' + "Host Cinder config file path not found: " +
                                   '</li>' +
                                   '<li>' + nova_data['conf_source'] + '</li>')
                    error_type_found = True
                if not error_type_found:
                    error_text += ('<li>' + "Check Horizon logs for more details" + '</li>')
                # use HTML markup for better formatted text
                status = mark_safe(error_text)
                raise ValidationError(status)

        return data

    def handle(self, request, data):
        try:
            config_status = ''
            software_status = ''

            if self.options_test_results:
                json_string = self.options_test_results
                parsed_json = json.loads(json_string)
                for section in parsed_json:
                    config_status += \
                        "Backend Section:" + section['Backend Section'] + "::" + \
                        "cpg:" + section['CPG'] + "::" + \
                        "credentials: " + section['Credentials'] + "::" + \
                        "driver:" + section['Driver'] + "::" + \
                        "wsapi:" + section['WS API'] + "::" + \
                        "iscsi:" + section['iSCSI IP(s)'] + "::"

            if self.software_test_results:
                json_string = self.software_test_results
                parsed_json = json.loads(json_string)
                for section in parsed_json:
                    software_pkg = "Software Test:package:"
                    if section['Node'].endswith("nova"):
                        software_pkg += "[Nova] " + section['Software']
                    else:
                        software_pkg += "[Cinder] " + section['Software']
                    software_status += \
                        software_pkg + "::" + \
                        "installed:" + section['Installed'] + "::" + \
                        "version:" + section['Version'] + "::"

            # update test data
            self.barbican_api.delete_diag_test(self.keystone_api.get_session_key(),
                                               self.test['test_name'])

            import oslo_utils
            time = oslo_utils.timeutils.utcnow()
            self.barbican_api.add_diag_test(self.keystone_api.get_session_key(),
                                            self.test['test_name'],
                                            self.test['service_type'],
                                            self.test['host_ip'],
                                            self.test['ssh_name'],
                                            self.test['ssh_pwd'],
                                            self.test['config_path'],
                                            config_status,
                                            software_status,
                                            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

            messages.success(request, _('Successfully ran diagnostic test'))
            return True
        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to run diagnostic test: ') + ex.message,
                              redirect=redirect)

