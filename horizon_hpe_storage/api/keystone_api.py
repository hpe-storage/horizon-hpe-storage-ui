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

    def do_setup(self, request):
        session = request.session
        # if 'unscoped_token' in session:
        #     token = request.session['unscoped_token']
        # else:
        #     token = request.session._session['token'].unscoped_token
        try:
            token = request.session['unscoped_token']
            tenant_id = request.session._session['token'].project['id']
            self.client = client.KeystoneClient(self.keystone_api_url)
            self.client.initClient(token, tenant_id)
        except Exception as ex:
            return
        if self.debug:
            self.client.debug_rest(True)

    # def get_session_token(self):
    #     LOG.debug("Requesting Token from Keystone")
    #     return self.client.getSessionKeystoneToken(self.keystone_username,
    #                                                self.keystone_passwd)

    def get_session_key(self):
        return self.client.getSessionKey()

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