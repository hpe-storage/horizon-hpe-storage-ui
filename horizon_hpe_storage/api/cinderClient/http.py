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

try:
    import json
except ImportError:
    import simplejson as json

from horizon_hpe_storage.api.common import exceptions
from horizon_hpe_storage.api.common import http


class HTTPJSONRESTClient(http.HTTPJSONRESTClient):
    """
    HTTP/REST client to access cinder service
    """

    def getHostCapabilities(self, token, tenant_id, host):
        try:
            capabilities = []
            self.auth_try = 1
            header = {'X-Auth-Token': token}
            resp, body = self.get('/v2/' + tenant_id +
                                  '/capabilities/' + host,
                                  headers=header)
            if body and 'properties' in body:
                properties = body['properties']
                for capability, details in properties.iteritems():
                    new_capability = {}
                    new_capability['name'] = details['title']
                    new_capability['description'] = details['description']
                    capabilities.append(new_capability)

            return capabilities
        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to get Host capabilities.'))
