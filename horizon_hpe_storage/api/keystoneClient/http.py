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
    HTTP/REST client to access keystone service
    """

    def initClient(self, token, tenant_id):
        # use the unscoped token from the Horizon session to get a
        # real admin token that we can use to access Keystone and Barbican
        self.token_id = None
        self.auth_try = 0
        try:
            info = {
                'auth': {
                    'tenantId': tenant_id,
                    'token': {
                        'id': token
                    }
                }
            }

            resp, body = self.post('/v2.0/tokens', body=info)
            if body and 'access' in body:
                access = body['access']
                if 'token' in access:
                    newToken = access['token']
                    self.token_id = newToken['id']
                    self.tenant_id = tenant_id
        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to get Keystone token.'))

    def getTokenId(self):
        return self.token_id

    def getTenantId(self):
        return self.tenant_id

    def getSSMCEndpointForHost(self, host):
        try:
            # first get service id
            header = {'X-Auth-Token': self.token_id}

            resp, body = self.get(
                '/v3/services?name=ssmc-' + host,
                headers=header)

            if body and 'services' in body:
                services = body['services']
                service = services[0]
                if service and 'id' in service:
                    service_id = service['id']

            # now get endpoint for this service
            if service_id:
                resp, body = self.get('/v3/endpoints?service_id=' +
                                      service_id, headers=header)
                if body and 'endpoints' in body:
                    endpoints = body['endpoints']
                    endpoint = endpoints[0]
                    return endpoint['url']

            return None
        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to get SSMC Endpoint for host.'))

    def getSSMCEndpointForServiceName(self, service_name):
        # first get service id
        header = {'X-Auth-Token': self.token_id}

        resp, body = self.get(
            '/v3/services?name=ssmc-3parfc',
            headers=header)
        if body and 'services' in body:
            services = body['services']
            service = services[0]
            if service and 'id' in service:
                service_id = service['id']

        # now get endpoint for this service
        if service_id:
            resp, body = self.get(
                '/v3/endpoints?service_id=' +
                service_id, headers=header)
            if body and 'endpoints' in body:
                endpoints = body['endpoints']
                endpoint = endpoints[0]
                return endpoint['url'], service_id

        return None

    def getSSMCEndpointForServiceId(self, service_id):
        # first get service id
        header = {'X-Auth-Token': self.token_id}

        url = '/v3/services/' + service_id
        resp, body = self.get(url, headers=header)
        if body and 'service' in body:
            service = body['service']
            if service and 'id' in service:
                service_id = service['id']
                service_name = service['name']

        # now get endpoint for this service
        if service_id:
            resp, body = self.get('/v3/endpoints?service_id=' +
                                  service_id, headers=header)
            if body and 'endpoints' in body:
                endpoints = body['endpoints']
                if endpoints:
                    endpoint = endpoints[0]
                    return endpoint, service_name

        return None

    def getSSMCServiceName(self, service_id):
        header = {'X-Auth-Token': self.token_id}

        url = '/v3/services/' + service_id
        resp, body = self.get(url, headers=header)
        if body and 'service' in body:
            service = body['service']
            if service and 'name' in service:
                service_name = service['name']
                return service_name
        return None

    def getSSMCEndpoints(self):
        endpoints = []
        # get all 3par-link services
        self.auth_try = 1
        header = {'X-Auth-Token': self.token_id}
        try:
            resp, body = self.get(
                '/v3/services?type=3par-link',
                headers=header)
            if body and 'services' in body:
                services = body['services']
                # get endpoint for each service
                for service in services:
                    if service and 'id' in service:
                        id = service['id']
                        endpt, name = self.getSSMCEndpointForServiceId(id)
                        if endpt:
                            endpointData = {}
                            endpointData['id'] = service['id']
                            backend = name[5:]    # remove 'ssmc-' prefix
                            endpointData['backend'] = backend
                            endpointData['endpoint'] = endpt['url']
                            endpoints.append(endpointData)

            return endpoints
        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to get SSMC Endpoints.'))

    def addSSMCEndpoint(self, service_name, endpoint):
        # first add service
        header = {'X-Auth-Token': self.token_id}
        info = {
            'service': {
                'type': '3par-link',
                'name': service_name,
                'description': 'link to SSMC instance'
            }
        }
        resp, body = self.post('/v3/services', headers=header, body=info)

        # now add endpoint for service
        if body and 'service' in body:
            service = body['service']
            if service and 'id' in service:
                service_id = service['id']
                if service_id:
                    info = {
                        'endpoint': {
                            'interface': 'admin',
                            'region': 'RegionOne',
                            'url': endpoint,
                            'service_id': service_id
                        }
                    }
                    resp, body = self.post(
                        '/v3/endpoints',
                        headers=header,
                        body=info)

    def updateSSMCEndpointUrl(self, service_id, url):
        # first need to get endpoint id
        endpt, service_name = self.getSSMCEndpointForServiceId(service_id)
        endpt_id = endpt['id']
        header = {'X-Auth-Token': self.token_id}
        # update endpoint for service
        try:
            info = {
                'endpoint': {
                    'interface': 'admin',
                    'region': 'RegionOne',
                    'url': url,
                    'service_id': service_id
                }
            }
            resp, body = self.patch(
                '/v3/endpoints/' + endpt_id,
                headers=header,
                body=info)
        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to update SSMC Endpoint URL.'))

    def deleteSSMCEndpoint(self, service_id):
        header = {'X-Auth-Token': self.token_id}
        try:
            # first delete endpoint for the service
            endpt, service_name = self.getSSMCEndpointForServiceId(service_id)
            resp = self.delete('/v3/endpoints/' + endpt['id'], headers=header)

            # now delete the service
            resp = self.delete('/v3/services/' + service_id, headers=header)
        except Exception as ex:
            exceptions.handle(self.request,
                              'Unable to delete SSMC Endpoint.')
