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

from cinderClient import client

import logging

LOG = logging.getLogger(__name__)

class CinderAPI(object):

    def __init__(self):
        self.client = None
        self.uuid = uuid.uuid4()
        openstack_host = getattr(settings, 'OPENSTACK_HOST')
        self.cinder_api_url = 'http://' + openstack_host + ':8776'
        self.debug = True
        self.launch_page = self.cinder_api_url + '/#/launch-page/'
        self.showUrl = '/virtual-volumes/show/overview/r'

    def _create_client(self):
        cl = client.CinderClient(self.cinder_api_url)
        return cl

    def do_setup(self, context):
        try:
            self.client = self._create_client()
        except Exception as ex:
            return
        if self.debug:
            self.client.debug_rest(True)

    # def get_pools(self, token, tenant_id):
    #     return self.client.getCinderPools(token, tenant_id)

    def get_capabilities(self, token, tenant_id, host):
        return self.client.getHostCapabilities(token, tenant_id, host)
