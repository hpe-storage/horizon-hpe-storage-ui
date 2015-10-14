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

import uuid

from django.conf import settings

from barbicanClient import client

import logging

LOG = logging.getLogger(__name__)

class BarbicanAPI(object):

    def __init__(self):
        self.client = None
        self.uuid = uuid.uuid4()
        openstack_host = getattr(settings, 'OPENSTACK_HOST')
        self.barbican_api_url = 'http://' + openstack_host + ':9311'
        self.debug = True
        self.launch_page = self.barbican_api_url + '/#/launch-page/'
        self.showUrl = '/virtual-volumes/show/overview/r'

    def _create_client(self):
        cl = client.BarbicanClient(self.barbican_api_url)
        return cl

    def do_setup(self, context):
        try:
            self.client = self._create_client()
        except Exception as ex:
            return
        if self.debug:
            self.client.debug_rest(True)

    def get_credentials(self, token, host):
        return self.client.getCredentials(token, host)

    def add_credentials(self, token, host, uname, pwd):
        return self.client.addCredentials(token, host, uname, pwd)

    def update_user_name(self, token, host, uname):
        return self.client.updateUserName(token, host, uname)

    def update_password(self, token, host, pwd):
        return self.client.updatePassword(token, host, pwd)

    def delete_credentials(self, token, host):
        return self.client.deleteCredentials(token, host)

    def add_diag_test(self, token, test_name, service_type, host_ip,
                      ssh_name, ssh_pwd, config_path, config_status=None,
                      software_status=None, run_time=None):
        return self.client.addDiagTest(token, test_name, service_type,
                                       host_ip, ssh_name, ssh_pwd,
                                       config_path, config_status,
                                       software_status, run_time)

    def get_all_diag_tests(self, token):
        return self.client.getAllDiagTests(token)

    def get_diag_test(self, token, name):
        return self.client.getDiagTest(token, name)

    def delete_diag_test(self, token, name):
        return self.client.deleteDiagTest(token, name)

