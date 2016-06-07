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

import http


class KeystoneClient(object):

    """ Client layer to access HTTP calls to Keystone backend.

    Would prefer to use python-keystoneclient directly, but found
    issues manipulating services and endpoints with default
    Horizon login token.

    TODO use python-keystoneclient instead of HTTP/REST calls
    """

    def __init__(self, api_url):
        self.api_url = api_url
        self.http = http.HTTPJSONRESTClient(self.api_url)
        api_version = None

    def initClient(self, token, tenant_id):
        self.http.initClient(token, tenant_id)

    def debug_rest(self, flag):
        """This is useful for debugging requests.

        :param flag: set to True to enable debugging
        :type flag: bool

        """
        self.http.set_debug_flag(flag)

    # def getSessionKey(self):
    #     return self.http.getSessionKey()

    def getTokenId(self):
        return self.http.getTokenId()

    def getTenantId(self):
        return self.http.getTenantId()

    def getSSMCEndpointForHost(self, host_name):
        return self.http.getSSMCEndpointForHost(host_name)

    def getSSMCEndpointForServiceName(self, service_name):
        return self.http.getSSMCEndpointForServiceName(service_name)

    def getSSMCEndpointForServiceId(self, service_id):
        return self.http.getSSMCEndpointForServiceId(service_id)

    def getSSMCServiceName(self, service_id):
        return self.http.getSSMCServiceName(service_id)

    def getSSMCEndpoints(self):
        return self.http.getSSMCEndpoints()

    def addSSMCEndpoint(self, service_name, endpoint):
        return self.http.addSSMCEndpoint(service_name, endpoint)

    def updateSSMCEndpointUrl(self, service_id, endpoint):
        return self.http.updateSSMCEndpointUrl(service_id, endpoint)

    def deleteSSMCEndpoint(self, service_id):
        return self.http.deleteSSMCEndpoint(service_id)
