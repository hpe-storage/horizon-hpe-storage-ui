# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2012 Hewlett Packard Development Company, L.P.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
""" HTTPJSONRESTClient.

.. module: http

:Author: Walter A. Boring IV
:Description: This is the HTTP Client that is used to make the actual calls.
 It includes the authentication that knows the cookie name for 3PAR.

"""

try:
    import json
except ImportError:
    import simplejson as json

from horizon_ssmc_link.api.common import exceptions
from horizon_ssmc_link.api.common import http


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

    def authenticateKeystone(self, user, password, optional=None):
        """
        This tries to create an authenticated session with the 3PAR server

        :param user: The username
        :type user: str
        :param password: Password
        :type password: str

        """
        # this prevens re-auth attempt if auth fails
        self.auth_try = 1
        self.session_key = None

        info = {'auth':
                     {'tenantName': 'admin',
                      'passwordCredentials':
                           {'username': user,
                            'password': password
                           }
                     }
               }

        self._auth_optional = None

        if optional:
            self._auth_optional = optional
            info.update(optional)

        resp, body = self.post('/v2.0/tokens', body=info)
        if body and 'access' in body:
            access = body['access']
            if access and 'token' in access:
                token = access['token']
                if token and 'id' in token:
                    self.session_key = token['id']
                if token and 'tenant' in token:
                    tenant = token['tenant']
                    if tenant and 'id' in tenant:
                        self.tenant_id = tenant['id']


        self.auth_try = 0
        self.user = user
        self.password = password

    def getSessionKey(self):
        return self.session_key

    def getTenantId(self):
        return self.tenant_id

    def getSSMCEndpointForHost(self, host):
        try:
            # first get service id
            header = {'X-Auth-Token': self.getSessionKey()}

            resp, body = self.get('/v3/services?name=ssmc-' + host, headers=header)
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
        header = {'X-Auth-Token': self.getSessionKey()}

        resp, body = self.get('/v3/services?name=ssmc-3parfc', headers=header)
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
                return endpoint['url'], service_id

        return None

    def getSSMCEndpointForServiceId(self, service_id):
        # first get service id
        header = {'X-Auth-Token': self.getSessionKey()}

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
        header = {'X-Auth-Token': self.getSessionKey()}

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
        header = {'X-Auth-Token': self.getSessionKey()}
        try:
            resp, body = self.get('/v3/services?type=3par-link', headers=header)
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
        header = {'X-Auth-Token': self.getSessionKey()}
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
                    resp, body = self.post('/v3/endpoints', headers=header, body=info)

    def updateSSMCEndpointUrl(self, service_id, url):
        # first need to get endpoint id
        endpt, service_name = self.getSSMCEndpointForServiceId(service_id)
        endpt_id = endpt['id']
        header = {'X-Auth-Token': self.getSessionKey()}
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
            resp, body = self.patch('/v3/endpoints/' + endpt_id, headers=header, body=info)
        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to update SSMC Endpoint URL.'))

    def deleteSSMCEndpoint(self, service_id):
        header = {'X-Auth-Token': self.getSessionKey()}
        try:
            # first delete endpoint for the service
            endpt, service_name = self.getSSMCEndpointForServiceId(service_id)
            resp = self.delete('/v3/endpoints/' + endpt['id'], headers=header)

            # now delete the service
            resp = self.delete('/v3/services/' + service_id, headers=header)
        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to delete SSMC Endpoint.'))

    def _reauth(self):
        self.authenticateKeystone(self.user, self.password, self._auth_optional)

    def unauthenticateKeystone(self):
        """
        This clears the authenticated session with the 3PAR server.

        """
        # delete the session on the 3Par
        # TODO How to Delete Keystone Session Key????
        #self.delete('/foundation/REST/sessionservice/sessions/%s' % self.session_key)
        #self.session_key = None