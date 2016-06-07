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

from keystoneClient import client
from keystoneclient.v2_0 import client as k_client
from keystoneclient.v3 import client as k3_client
from keystoneauth1 import session as k_session

from openstack_dashboard.api import keystone as horizon_keystone


import logging

LOG = logging.getLogger(__name__)


class KeystoneAPI(object):

    def __init__(self):
        openstack_host = getattr(settings, 'OPENSTACK_HOST')
        self.client = None
        self.uuid = uuid.uuid4()
        self.keystone_api_url = 'http://' + openstack_host + ':5000'
        self.debug = True
        self.launch_page = self.keystone_api_url + '/#/launch-page/'
        self.showUrl = '/virtual-volumes/show/overview/r'
        self.token = None
        self.session = None

    def do_setup(self, request):
        try:
            cur_token = request.session['unscoped_token']
            # only init new cliet with admin token if token has expired and
            # been re-issued (i.e. user had to log back in)
            if self.token != cur_token:
                self.token = cur_token
                tenant_id = request.session._session['token'].project['id']
                self.client = client.KeystoneClient(self.keystone_api_url)
                self.client.initClient(self.token, tenant_id)
                if self.debug:
                    self.client.debug_rest(True)

                keystone_client = k_client.Client(
                    token=self.get_token_id(),
                    endpoint=self.keystone_api_url + "/v2.0",
                    tenant_name='admin')
                self.session = k_session.Session(auth=keystone_client)

        except Exception as ex:
            return

    def get_session(self):
        return self.session

    def get_token_id(self):
        return self.client.getTokenId()

    def get_tenant_id(self):
        return self.client.getTenantId()

    def get_ssmc_endpoint_for_host(self, host_name):
        return self.client.getSSMCEndpointForHost(host_name)

    def get_ssmc_endpoint_for_service_name(self, service_name):
        return self.client.getSSMCEndpointForServiceName(service_name)

    def get_ssmc_endpoint_for_service_id(self, service_id):
        return self.client.getSSMCEndpointForServiceId(service_id)

    def get_ssmc_service_name(self, service_id):
        return self.client.getSSMCServiceName(service_id)

    def get_ssmc_endpoints(self):
        return self.client.getSSMCEndpoints()

    def add_ssmc_endpoint(self, service_name, endpoint):
        return self.client.addSSMCEndpoint(service_name, endpoint)

    def update_ssmc_endpoint_url(self, service_id, endpoint):
        return self.client.updateSSMCEndpointUrl(service_id, endpoint)

    def delete_ssmc_endpoint(self, service_id):
        return self.client.deleteSSMCEndpoint(service_id)
