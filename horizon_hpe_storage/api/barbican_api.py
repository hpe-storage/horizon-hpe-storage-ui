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


import logging

LOG = logging.getLogger(__name__)
class BarbicanAPI(object):

    CINDER_NODE_TYPE = 'cinder'
    NOVA_NODE_TYPE = 'nova'
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
        nodeData = {}
        container  = self._get_container(type + '-cinderdiags-' + name)
        if container:
            srefs = container.secret_refs
            for key, value in srefs.items():
                data = self.client.secrets.get(value).payload
                # pull out the meta data about the test
                if key == 'meta_test_data':
                    raw_results = data.split("###")
                    for raw_result in raw_results:
                        entry = raw_result.split("%%%")
                        nodeData[entry[0]] = entry[1]
                else:
                    nodeData[key] = data
            return nodeData
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
                    nodeData = {}
                    for key, value in srefs.items():
                        data = self.client.secrets.get(value).payload
                        # pull out the meta data about the test
                        if key == 'meta_test_data':
                            raw_results = data.split("###")
                            for raw_result in raw_results:
                                entry = raw_result.split("%%%")
                                nodeData[entry[0]] = entry[1]
                        else:
                            nodeData[key] = data
                    nodes.append(nodeData)
        return nodes

    def delete_node(self, name, type):
        container  = self._get_container(type + '-cinderdiags-' + name)
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
        meta_data = ""

        # add meta data into one secret
        meta_data += "node_name" + "%%%" + name
        meta_data += "###"
        meta_data += "node_type" + "%%%" + type
        meta_data += "###"
        meta_data += "node_ip" + "%%%" + ip
        meta_data += "###"
        meta_data += "ssh_name" + "%%%" + ssh_name
        meta_data += "###"
        meta_data += "ssh_pwd" + "%%%" + ssh_pwd

        if config_path:
            meta_data += "###"
            meta_data += "config_path" + "%%%" + config_path

        if diag_run_time:
            meta_data += "###"
            meta_data += "diag_run_time" + "%%%" + diag_run_time

        if ssh_validation_time:
            meta_data += "###"
            meta_data += "validation_time" + "%%%" + ssh_validation_time

        if diag_status:
            meta_data += "###"
            meta_data += "diag_test_status" + "%%%" + diag_status

        if software_status:
            meta_data += "###"
            meta_data += "software_test_status" + "%%%" + software_status

        secret = self.client.secrets.create(
            name="meta_test_data",
            payload=meta_data)
        secrets['meta_test_data'] = secret

        # secret = self.client.secrets.create(
        #     name="node_name",
        #     payload=name)
        # secrets['node_name'] = secret
        #
        # secret = self.client.secrets.create(
        #     name="node_type",
        #     payload=type)
        # secrets['node_type'] = secret
        #
        # secret = self.client.secrets.create(
        #     name="node_ip",
        #     payload=ip)
        # secrets['node_ip'] = secret
        #
        # secret = self.client.secrets.create(
        #     name="ssh_name",
        #     payload=ssh_name)
        # secrets['ssh_name'] = secret
        #
        # secret = self.client.secrets.create(
        #     name="ssh_pwd",
        #     payload=ssh_pwd)
        # secrets['ssh_pwd'] = secret
        #
        # if config_path:
        #     secret = self.client.secrets.create(
        #         name="config_path",
        #         payload=config_path)
        #     secrets['config_path'] = secret
        #
        # if diag_status:
        #     secret = self.client.secrets.create(
        #         name="diag_test_status",
        #         payload=diag_status)
        #     secrets['diag_test_status'] = secret
        #
        # if software_status:
        #     secret = self.client.secrets.create(
        #         name="software_test_status",
        #         payload=software_status)
        #     secrets['software_test_status'] = secret
        #
        # if diag_run_time:
        #     secret = self.client.secrets.create(
        #         name="diag_run_time",
        #         payload=diag_run_time)
        #     secrets['diag_run_time'] = secret
        #
        # if ssh_validation_time:
        #     secret = self.client.secrets.create(
        #         name="validation_time",
        #         payload=ssh_validation_time)
        #     secrets['validation_time'] = secret

        # create container
        secret_list = {}
        secret_list['secrets'] = secrets
        node_name = type + '-cinderdiags-' + name
        node = self.client.containers.create(node_name,
                                             **secret_list)
        node.store()
        return node
