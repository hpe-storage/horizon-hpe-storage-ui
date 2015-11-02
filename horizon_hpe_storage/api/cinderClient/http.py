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
    An HTTP REST Client that sends and recieves JSON data as the body of the
    HTTP request.

    :param api_url: The url to the WSAPI service on 3PAR
                    ie. http://<3par server>:8080
    :type api_url: str
    :param insecure: Use https? requires a local certificate
    :type insecure: bool

    """

    def getCinderPools(self, token, tenant_id):
        try:
            backends = []
            self.auth_try = 1
            header = {'X-Auth-Token': token}
            resp, body = self.get('/v2/' + tenant_id +
                                  '/scheduler-stats/get_pools?detail=True',
                                  headers=header)
            if body and 'pools' in body:
                pools = body['pools']
                for pool in pools:
                    if 'capabilities' in pool:
                        capabilities = pool['capabilities']
                        if capabilities and 'volume_backend_name' in capabilities:
                            backend = capabilities['volume_backend_name']
                            backends.append(backend)
            return backends
        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to get Cinder pools.'))
