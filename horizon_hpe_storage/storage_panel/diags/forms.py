
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
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages

import logging

LOG = logging.getLogger(__name__)
import datetime
import json

import horizon_hpe_storage.api.keystone_api as keystone
import horizon_hpe_storage.api.barbican_api as barbican
import horizon_hpe_storage.test_engine.node_test as tester

from openstack_dashboard.api import cinder


def run_cinder_node_test(node, software_tests, barbican_api):
    credentials_data = {}
    all_data = []

    # note 'section' must be lower case for diag tool
    credentials_data['section'] = \
        node['node_name'].lower() + '-' + barbican.CINDER_NODE_TYPE
    credentials_data['service'] = barbican.CINDER_NODE_TYPE
    credentials_data['host_ip'] = node['node_ip']
    credentials_data['ssh_user'] = node['ssh_name']
    credentials_data['ssh_password'] = node['ssh_pwd']
    credentials_data['conf_source'] = node['config_path']

    all_data.append(credentials_data)
    json_conf_data = json.dumps(all_data)

    # run ssh validation check on cinder node
    node_test = tester.NodeTest()
    node_test.run_credentials_check_test(json_conf_data)

    cur_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if "fail" in node_test.test_result_text:
        error_text = 'SSH credential validation failed'
        LOG.info(("%s") % node_test.error_text)

        # update test data
        barbican_api.delete_node(
            node['node_name'],
            barbican.CINDER_NODE_TYPE)

        result = "Failed"
        barbican_api.add_node(
            node['node_name'],
            barbican.CINDER_NODE_TYPE,
            node['node_ip'],
            node['ssh_name'],
            node['ssh_pwd'],
            config_path=node['config_path'],
            diag_run_time=cur_time,
            ssh_validation_time="Failed")

        # no need to continue
        return

    # run diag test on cinder node
    node_test.run_options_check_test(json_conf_data)

    config_status = ''
    LOG.info("Process test results - start options results")
    if node_test.test_result_text:
        json_string = node_test.test_result_text
        LOG.info("options:json results - %s" % json_string)
        parsed_json = json.loads(json_string)
        LOG.info("options:parsed_json results - %s" % parsed_json)
        for section in parsed_json:
            config_status += \
                "Backend Section:" + section['Backend Section'] + "::" + \
                "cpg:" + section['CPG'] + "::" + \
                "credentials: " + section['Credentials'] + "::" + \
                "driver:" + section['Driver'] + "::" + \
                "wsapi:" + section['WS API'] + "::" + \
                "iscsi:" + section['iSCSI IP(s)'] + "::" + \
                "system_info:" + section['System Info'] + "::" + \
                "config_items:" + section['Conf Items'] + "::"
            LOG.info("options:config_status - %s" % config_status)

    # build list of software to test against
    all_data = []
    sw_test_dict = {}
    for software_test in software_tests:
        sw_test_dict[software_test['package']] = software_test['min_version']
    all_data.append(sw_test_dict)
    json_sw_test_data = json.dumps(all_data)

    # run software test on cinder node
    node_test.run_software_check_test(json_conf_data, json_sw_test_data)

    software_status = ''
    LOG.info("Process test results - start software results")
    if node_test.test_result_text:
        json_string = node_test.test_result_text
        LOG.info("software:json results - %s" % json_string)
        parsed_json = json.loads(json_string)
        LOG.info("software:parsed_json results - %s" % parsed_json)
        for section in parsed_json:
            software_pkg = "Software Test:package:"
            software_pkg += section['Software']
            software_status += \
                software_pkg + "::" + \
                "installed:" + section['Installed'] + "::" + \
                "version:" + section['Version'] + "::"
            LOG.info("software:software_status - %s" % software_status)

    # update test data
    barbican_api.delete_node(
        node['node_name'],
        barbican.CINDER_NODE_TYPE)

    barbican_api.add_node(
        node['node_name'],
        barbican.CINDER_NODE_TYPE,
        node['node_ip'],
        node['ssh_name'],
        node['ssh_pwd'],
        config_path=node['config_path'],
        diag_status=config_status,
        software_status=software_status,
        diag_run_time=cur_time,
        ssh_validation_time=cur_time)


def run_nova_node_test(node, software_tests, barbican_api):
    credentials_data = {}
    all_data = []

    # note 'section' must be lower case for diag tool
    credentials_data['section'] = \
        node['node_name'].lower() + '-' + barbican.NOVA_NODE_TYPE
    credentials_data['service'] = barbican.NOVA_NODE_TYPE
    credentials_data['host_ip'] = node['node_ip']
    credentials_data['ssh_user'] = node['ssh_name']
    credentials_data['ssh_password'] = node['ssh_pwd']

    all_data.append(credentials_data)
    json_conf_data = json.dumps(all_data)

    # run ssh validation check on cinder node
    node_test = tester.NodeTest()
    node_test.run_credentials_check_test(json_conf_data)

    cur_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if "fail" in node_test.test_result_text:
        error_text = 'SSH credential validation failed'
        LOG.info(("%s") % node_test.error_text)

        # update test data
        barbican_api.delete_node(
            node['node_name'],
            barbican.NOVA_NODE_TYPE)

        result = "Failed"
        barbican_api.add_node(
            node['node_name'],
            barbican.NOVA_NODE_TYPE,
            node['node_ip'],
            node['ssh_name'],
            node['ssh_pwd'],
            diag_run_time=cur_time,
            ssh_validation_time="Failed")

        # no need to continue
        return

    # build list of software to test against
    all_data = []
    sw_test_dict = {}
    for software_test in software_tests:
        sw_test_dict[software_test['package']] = software_test['min_version']
    all_data.append(sw_test_dict)
    json_sw_test_data = json.dumps(all_data)

    # run software test on nova node
    node_test.run_software_check_test(json_conf_data, json_sw_test_data)

    software_status = ''
    LOG.info("Process test results - start software results")
    if node_test.test_result_text:
        json_string = node_test.test_result_text
        LOG.info("software:json results - %s" % json_string)
        parsed_json = json.loads(json_string)
        LOG.info("software:parsed_json results - %s" % parsed_json)
        for section in parsed_json:
            software_pkg = "Software Test:package:"
            software_pkg += section['Software']
            software_status += \
                software_pkg + "::" + \
                "installed:" + section['Installed'] + "::" + \
                "version:" + section['Version'] + "::"
            LOG.info("software:software_status - %s" % software_status)

    # update test data
    barbican_api.delete_node(
        node['node_name'],
        barbican.NOVA_NODE_TYPE)

    barbican_api.add_node(
        node['node_name'],
        barbican.NOVA_NODE_TYPE,
        node['node_ip'],
        node['ssh_name'],
        node['ssh_pwd'],
        software_status=software_status,
        diag_run_time=cur_time,
        ssh_validation_time=cur_time)


class DumpCinder(forms.SelfHandlingForm):
    stats = forms.CharField(
        # max_length=10000,
        label=_("Results"),
        required=False,
        widget=forms.Textarea(
            attrs={'rows': 10, 'readonly': 'readonly'}))

    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def __init__(self, request, *args, **kwargs):
        super(DumpCinder, self).__init__(request, *args, **kwargs)

        stats_field = self.fields['stats']

        node_name = self.initial['node_name']
        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            node = self.barbican_api.get_node(
                node_name,
                barbican.CINDER_NODE_TYPE)

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
                            system_info = self.get_backend_system_info(
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

                    stats += "\n\tConfig Items ('cinder.conf'):\n" + \
                             config_items
                    stats += "\n\tTest Results for 'cinder.conf':\n" + \
                             test_results
                    stats += "\n\tSystem Information:\n" + \
                             system_info

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

            stats_field.initial = stats

        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to access diagnostic test.'),
                              redirect=redirect)

    def get_backend_system_info(self, data):
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

    def handle(self, request, data):
        return True


class TestCinder(forms.SelfHandlingForm):
    node_name = forms.CharField(
        max_length=255,
        label=_("Cinder Node"),
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()
    node = None

    def __init__(self, request, *args, **kwargs):
        super(TestCinder, self).__init__(request, *args, **kwargs)
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
                              _('Unable to run diagnostic test.'),
                              redirect=redirect)

    def handle(self, request, data):
        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())

            # pass along the current set of software tests
            sw_tests = self.barbican_api.get_software_tests(
                barbican.CINDER_NODE_TYPE)

            run_cinder_node_test(self.node, sw_tests, self.barbican_api)
            messages.success(request, _('Successfully ran diagnostic test'))
            return True
        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(
                request,
                _('Unable to run diagnostic test: ') + ex.message,
                redirect=redirect)


class TestAllCinder(forms.SelfHandlingForm):
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
                              _('Unable to run diagnostic test.'),
                              redirect=redirect)

    def handle(self, request, data):
        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())

            # pass along the current set of software tests
            sw_tests = self.barbican_api.get_software_tests(
                barbican.CINDER_NODE_TYPE)

            for node in self.nodes:
                run_cinder_node_test(node, sw_tests, self.barbican_api)

            messages.success(
                request,
                _('Successfully ran all diagnostic tests'))
            return True
        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(
                request,
                _('Unable to run diagnostic tests: ') + ex.message,
                redirect=redirect)


class TestNova(forms.SelfHandlingForm):
    node_name = forms.CharField(
        max_length=255,
        label=_("Nova Node"),
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()
    node = None

    def __init__(self, request, *args, **kwargs):
        super(TestNova, self).__init__(request, *args, **kwargs)
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
                              _('Unable to run diagnostic test.'),
                              redirect=redirect)

    def handle(self, request, data):
        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())

            # pass along the current set of software tests
            sw_tests = self.barbican_api.get_software_tests(
                barbican.NOVA_NODE_TYPE)

            run_nova_node_test(self.node, sw_tests, self.barbican_api)
            messages.success(request, _('Successfully ran diagnostic test'))
            return True
        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(
                request,
                _('Unable to run diagnostic test: ') + ex.message,
                redirect=redirect)


class TestAllNova(forms.SelfHandlingForm):
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
                              _('Unable to run diagnostic test.'),
                              redirect=redirect)

    def handle(self, request, data):
        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())

            # pass along the current set of software tests
            sw_tests = self.barbican_api.get_software_tests(
                barbican.NOVA_NODE_TYPE)

            for node in self.nodes:
                run_nova_node_test(node, sw_tests, self.barbican_api)

            messages.success(
                request,
                _('Successfully ran all diagnostic tests'))
            return True
        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(
                request,
                _('Unable to run diagnostic tests: ') + ex.message,
                redirect=redirect)
