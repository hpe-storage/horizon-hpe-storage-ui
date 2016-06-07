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

from django.conf import settings

from barbicanclient import client as b_client

import json
import logging

CINDER_NODE_TYPE = 'cinder'
NOVA_NODE_TYPE = 'nova'

LOG = logging.getLogger(__name__)


class BarbicanAPI(object):
    container_limit = 1000
    secret_limit = 50

    def __init__(self):
        self.client = None
        self.cur_keystone_session = None
        openstack_host = getattr(settings, 'OPENSTACK_HOST')
        self.barbican_api_url = 'http://' + openstack_host + ':9311'
        self.debug = True

    # core functions
    def do_setup(self, keystone_session):
        # only init new client if session has been updated - meaning
        # user logged in with new token
        if self.client and self.cur_keystone_session:
            if self.cur_keystone_session == keystone_session:
                return

        self.cur_keystone_session = keystone_session
        self.client = b_client.Client(
            session=keystone_session,
            endpoint=self.barbican_api_url)

    def _get_container(self, container_name):
        containers = self.client.containers.list(name=container_name,
                                                 limit=self.container_limit)
        for container in containers:
            if container.name == container_name:
                return container
        return None

    def _get_secret(self, secret_name):
        secrets = self.client.secrets.list(name=secret_name,
                                           limit=self.secret_limit)
        for secret in secrets:
            if secret.name == secret_name:
                return secret
        return None

    # SSMC link functions
    def get_ssmc_credentials(self, cinder_backend):
        uname = None
        pwd = None
        secret = self._get_secret('ssmc-' + cinder_backend + '-uname')
        if secret:
            uname = secret.payload
        secret = self._get_secret('ssmc-' + cinder_backend + '-pwd')
        if secret:
            pwd = secret.payload
        return uname, pwd

    def add_ssmc_credentials(self, cinder_backend, uname=None, pwd=None):
        if uname:
            secret = self.client.secrets.create(
                name='ssmc-' + cinder_backend + '-uname',
                payload=uname)
            if secret:
                secret.store()

        if pwd:
            secret = self.client.secrets.create(
                name='ssmc-' + cinder_backend + '-pwd',
                payload=pwd)
            if secret:
                secret.store()

    def delete_ssmc_credentials(self, cinder_backend):
        secret = self._get_secret('ssmc-' + cinder_backend + '-uname')
        if secret:
            self.client.secrets.delete(secret.secret_ref)

        secret = self._get_secret('ssmc-' + cinder_backend + '-pwd')
        if secret:
            self.client.secrets.delete(secret.secret_ref)

    def update_ssmc_credentials(self, cinder_backend, uname=None, pwd=None):
        self.delete_ssmc_credentials(cinder_backend)
        self.add_ssmc_credentials(cinder_backend, uname, pwd)

    # Cinder/Nova node registration and diagnostics functions
    def get_node(self, name, type):
        node_data = {}
        container = self._get_container(type + '-cinderdiags-' + name)
        if container:
            srefs = container.secret_refs
            for key, value in srefs.items():
                data_str = self.client.secrets.get(value).payload
                data = json.loads(data_str)
                # pull out the meta data about the test
                meta_data = data["meta_data"]
                for key, value in meta_data.iteritems():
                    node_data[key] = value

                if 'diag_test_status' in data:
                    node_data['diag_test_status'] = \
                        data['diag_test_status']

                if 'software_test_status' in data:
                    node_data['software_test_status'] = \
                        data['software_test_status']

            return node_data
        return None

    def nodes_exist(self, type):
        containers = self.client.containers.list(limit=self.container_limit)
        for container in containers:
            if container.name.startswith(type + "-cinderdiags-"):
                return True

        return False

    def get_all_nodes(self, type):
        nodes = []
        containers = self.client.containers.list(limit=self.container_limit)
        for container in containers:
            if container.name.startswith(type):
                srefs = container.secret_refs
                if srefs:
                    node_data = {}
                    for key, value in srefs.items():
                        data_str = self.client.secrets.get(value).payload
                        data = json.loads(data_str)
                        # pull out the meta data about the test
                        meta_data = data["meta_data"]
                        for key, value in meta_data.iteritems():
                            node_data[key] = value

                        if 'diag_test_status' in data:
                            node_data['diag_test_status'] = \
                                data['diag_test_status']

                        if 'software_test_status' in data:
                            node_data['software_test_status'] = \
                                data['software_test_status']

                        nodes.append(node_data)
        return nodes

    def delete_node(self, name, type):
        container = self._get_container(type + '-cinderdiags-' + name)
        if container and container.secrets:
            # first delete all contained secrets
            for name, secret in container.secrets.items():
                self.client.secrets.delete(secret.secret_ref)

            # now delete container
            self.client.containers.delete(container.container_ref)

    def add_node(self, name, type, ip,
                 ssh_name, ssh_pwd, config_path=None, diag_status=None,
                 software_status=None, diag_run_time=None,
                 ssh_validation_time=None):
        # first create secret for each field
        secrets = {}

        node_data = {}

        meta_data = {}
        meta_data["node_name"] = name
        meta_data["node_type"] = type
        meta_data["node_ip"] = ip
        meta_data["ssh_name"] = ssh_name
        meta_data["ssh_pwd"] = ssh_pwd

        if config_path:
            meta_data["config_path"] = config_path

        if diag_run_time:
            meta_data["diag_run_time"] = diag_run_time

        if ssh_validation_time:
            meta_data["validation_time"] = ssh_validation_time

        node_data["meta_data"] = meta_data

        if diag_status:
            node_data["diag_test_status"] = diag_status

        if software_status:
            node_data["software_test_status"] = software_status

        # store as json string
        node_data_str = json.dumps(node_data)
        secret = self.client.secrets.create(
            name="node_data",
            payload=node_data_str)
        secrets['node_data'] = secret

        # create container
        secret_list = {}
        secret_list['secrets'] = secrets
        node_name = type + '-cinderdiags-' + name
        node = self.client.containers.create(node_name,
                                             **secret_list)
        node.store()
        return node

    # Software Tests API
    def _delete_software_test_container(self, type):
        container = self._get_container('diag-software-tests-' + type)
        if container and container.secrets:
            # first delete all contained secrets
            for name, secret in container.secrets.items():
                self.client.secrets.delete(secret.secret_ref)

            # now delete container
            self.client.containers.delete(container.container_ref)

    def _add_software_tests(self, type, tests):
        test_data = {}
        test_data['node_type'] = type
        test_data['software_tests'] = tests

        # store as json string
        secrets = {}
        test_data_str = json.dumps(test_data)
        secret = self.client.secrets.create(
            name="test_data",
            payload=test_data_str)
        secrets['test_data'] = secret

        # create container
        secret_list = {}
        secret_list['secrets'] = secrets
        test_name = 'diag-software-tests-' + type
        test = self.client.containers.create(test_name,
                                             **secret_list)
        test.store()
        return test

    def get_software_tests(self, type):
        test_data = {}
        container = self._get_container('diag-software-tests-' + type)
        if container:
            srefs = container.secret_refs
            for key, value in srefs.items():
                data_str = self.client.secrets.get(value).payload
                data = json.loads(data_str)
                if 'software_tests' in data:
                    return data["software_tests"]
        else:
            # if no container exists, we are creating the first test, so
            # seed with some standard tests
            tests = []
            software_pkg = {}
            software_pkg['package'] = 'sg3-utils || sg3_utils'
            software_pkg['min_version'] = '1.3'
            software_pkg['description'] = \
                'required for attaching FC volumes'
            tests.append(software_pkg)
            software_pkg = {}
            software_pkg['package'] = 'sysfsutils'
            software_pkg['min_version'] = '2.1'
            software_pkg['description'] = \
                'required for attaching FC volumes'
            tests.append(software_pkg)

            if type == CINDER_NODE_TYPE:
                software_pkg = {}
                software_pkg['package'] = 'python-3parclient'
                software_pkg['min_version'] = '4.2.0'
                software_pkg['description'] = \
                    'required for accessing HPE 3PAR array'
                tests.append(software_pkg)
            self._add_software_tests(type, tests)
            return tests

        return None

    def update_software_test(self, type, software_pkg,
                             min_version, description):
        # just update the one package
        new_tests = []
        curr_tests = self.get_software_tests(type)
        if curr_tests:
            for curr_test in curr_tests:
                if curr_test['package'] == software_pkg:
                    test = {}
                    test['package'] = software_pkg
                    test['min_version'] = min_version
                    test['description'] = description
                    new_tests.append(test)
                else:
                    new_tests.append(curr_test)

            # delete the old tests
            self._delete_software_test_container(type)

            self._add_software_tests(type, new_tests)

    def add_software_test(self, type, software_pkg,
                          min_version, description):
        tests = []

        curr_tests = self.get_software_tests(type)
        if curr_tests:
            tests = curr_tests
            # delete the old tests
            self._delete_software_test_container(type)

        new_test = {}
        new_test['package'] = software_pkg
        new_test['min_version'] = min_version
        new_test['description'] = description
        tests.append(new_test)

        return self._add_software_tests(type, tests)

    def delete_software_test(self, type, software_pkg):
        # can't update, so delete current tests and add back new
        curr_tests = self.get_software_tests(type)
        self._delete_software_test_container(type)

        new_tests = []
        for test in curr_tests:
            if test['package'] != software_pkg:
                new_tests.append(test)

        self._add_software_tests(type, new_tests)

    def delete_all_software_tests(self, type):
        # can't update, so delete all old and add back empty list
        self._delete_software_test_container(type)
        new_tests = []
        self._add_software_tests(type, new_tests)
