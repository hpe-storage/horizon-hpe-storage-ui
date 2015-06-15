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

import logging
import httplib2
import time
import pprint
import re

try:
    import json
except ImportError:
    import simplejson as json

from ssmc_link_ui.api.common import exceptions
from ssmc_link_ui.api.common import data


class HTTPJSONRESTClient(httplib2.Http):
    """
    An HTTP REST Client that sends and recieves JSON data as the body of the
    HTTP request.

    :param api_url: The url to the WSAPI service on 3PAR
                    ie. http://<3par server>:8080
    :type api_url: str
    :param insecure: Use https? requires a local certificate
    :type insecure: bool

    """

    USER_AGENT = 'python-3parclient'
    SESSION_COOKIE_NAME = 'Authorization'


    def __init__(self, api_url, insecure=False, http_log_debug=True):
        super(HTTPJSONRESTClient, self).__init__(
            disable_ssl_certificate_validation=True)

        self.session_key = None

        # should be http://<Server:Port>/api/v1
        self.set_url(api_url)
        self.set_debug_flag(http_log_debug)

        self.times = []  # [("item", starttime, endtime), ...]

        # httplib2 overrides
        self.force_exception_to_status_code = True
        # self.disable_ssl_certificate_validation = insecure

        self._logger = logging.getLogger(__name__)

    def set_url(self, api_url):
        # should be http://<Server:Port>/api/v1
        self.api_url = api_url.rstrip('/')

    def set_debug_flag(self, flag):
        """
        This turns on/off http request/response debugging output to console

        :param flag: Set to True to enable debugging output
        :type flag: bool

        """
        self.http_log_debug = flag
        if self.http_log_debug:
            ch = logging.StreamHandler()
            #self._logger.setLevel(logging.DEBUG)
            #self._logger.addHandler(ch)

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
            i = 0

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
            i = 10

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
            i = 0

    def deleteSSMCEndpoint(self, service_id):
        header = {'X-Auth-Token': self.getSessionKey()}
        try:
            # first delete endpoint for the service
            endpt, service_name = self.getSSMCEndpointForServiceId(service_id)
            resp = self.delete('/v3/endpoints/' + endpt['id'], headers=header)

            # now delete the service
            resp = self.delete('/v3/services/' + service_id, headers=header)
        except Exception as ex:
            i = 10

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

    def get_timings(self):
        """
        Ths gives an array of the request timings since last reset_timings call
        """
        return self.times

    def reset_timings(self):
        """
        This resets the request/response timings array
        """
        self.times = []

    def _http_log_req(self, args, kwargs):
        if not self.http_log_debug:
            return

        string_parts = ['curl -i']
        for element in args:
            if element in ('GET', 'POST'):
                string_parts.append(' -X %s' % element)
            else:
                string_parts.append(' %s' % element)

        for element in kwargs['headers']:
            header = ' -H "%s: %s"' % (element, kwargs['headers'][element])
            string_parts.append(header)

        self._logger.debug("\nREQ: %s\n" % "".join(string_parts))
        if 'body' in kwargs:
            self._logger.debug("REQ BODY: %s\n" % (kwargs['body']))

    def _http_log_resp(self, resp, body):
        if not self.http_log_debug:
            return
        self._logger.debug("RESP:%s\n", pprint.pformat(resp))
        self._logger.debug("RESP BODY:%s\n", body)

    def request(self, *args, **kwargs):
        """
        This makes an HTTP Request to the 3Par server.
        You should use get, post, delete instead.

        """
        if self.session_key and self.auth_try != 1:
            kwargs.setdefault('headers', {})[self.SESSION_COOKIE_NAME] = \
                self.session_key

        kwargs.setdefault('headers', kwargs.get('headers', {}))
        #kwargs['headers']['User-Agent'] = self.USER_AGENT
        kwargs['headers']['Accept'] = 'application/json'
        if 'body' in kwargs:
            kwargs['headers']['Content-Type'] = 'application/json'
            kwargs['body'] = json.dumps(kwargs['body'])

        self._http_log_req(args, kwargs)
        resp, body = super(HTTPJSONRESTClient, self).request(*args, **kwargs)
        self._http_log_resp(resp, body)

        # Try and conver the body response to an object
        # This assumes the body of the reply is JSON
        if body:
            try:
                body = json.loads(body)
            except ValueError:
                pass
        else:
            body = None

        if resp.status >= 400:
            raise exceptions.from_response(resp, body)

        return resp, body

    def _time_request(self, url, method, **kwargs):
        start_time = time.time()
        resp, body = self.request(url, method, **kwargs)
        self.times.append(("%s %s" % (method, url),
                           start_time, time.time()))
        return resp, body

    def _do_reauth(self, url, method, ex, **kwargs):
        # print("_do_reauth called")
        try:
            if self.auth_try != 1:
                self._reauth()
                resp, body = self._time_request(self.api_url + url, method,
                                                **kwargs)
                return resp, body
            else:
                raise ex
        except exceptions.HTTPUnauthorized:
            raise ex

    def _cs_request(self, url, method, **kwargs):
        # Perform the request once. If we get a 401 back then it
        # might be because the auth token expired, so try to
        # re-authenticate and try again. If it still fails, bail.
        try:
            resp, body = self._time_request(self.api_url + url, method,
                                            **kwargs)
            return resp, body
        except exceptions.HTTPUnauthorized as ex:
            # print("_CS_REQUEST HTTPUnauthorized")
            resp, body = self._do_reauth(url, method, ex, **kwargs)
            return resp, body
        except exceptions.HTTPForbidden as ex:
            # print("_CS_REQUEST HTTPForbidden")
            resp, body = self._do_reauth(url, method, ex, **kwargs)
            return resp, body

    def get(self, url, **kwargs):
        """
        Make an HTTP GET request to the server.

        .. code-block:: python

            #example call
            try {
                headers, body = http.get('/volumes')
            } except exceptions.HTTPUnauthorized as ex:
                print "Not logged in"
            }

        :param url: The relative url from the 3PAR api_url
        :type url: str

        :returns: headers - dict of HTTP Response headers
        :returns: body - the body of the response.  If the body was JSON, it
                         will be an object
        """
        return self._cs_request(url, 'GET', **kwargs)

    def post(self, url, **kwargs):
        """
        Make an HTTP POST request to the server.

        .. code-block:: python

            #example call
            try {
                info = {'name': 'new volume name', 'cpg': 'MyCPG',
                        'sizeMiB': 300}
                headers, body = http.post('/volumes', body=info)
            } except exceptions.HTTPUnauthorized as ex:
                print "Not logged in"
            }

        :param url: The relative url from the 3PAR api_url
        :type url: str

        :returns: headers - dict of HTTP Response headers
        :returns: body - the body of the response.  If the body was JSON, it
                         will be an object
        """
        return self._cs_request(url, 'POST', **kwargs)

    def put(self, url, **kwargs):
        """
        Make an HTTP PUT request to the server.

        .. code-block:: python

            #example call
            try {
                info = {'name': 'something'}
                headers, body = http.put('/volumes', body=info)
            } except exceptions.HTTPUnauthorized as ex:
                print "Not logged in"
            }

        :param url: The relative url from the 3PAR api_url
        :type url: str

        :returns: headers - dict of HTTP Response headers
        :returns: body - the body of the response.  If the body was JSON,
                         it will be an object
        """
        return self._cs_request(url, 'PUT', **kwargs)

    def patch(self, url, **kwargs):
        """
        Make an HTTP PUT request to the server.

        .. code-block:: python

            #example call
            try {
                info = {'name': 'something'}
                headers, body = http.put('/volumes', body=info)
            } except exceptions.HTTPUnauthorized as ex:
                print "Not logged in"
            }

        :param url: The relative url from the 3PAR api_url
        :type url: str

        :returns: headers - dict of HTTP Response headers
        :returns: body - the body of the response.  If the body was JSON,
                         it will be an object
        """
        return self._cs_request(url, 'PATCH', **kwargs)

    def delete(self, url, **kwargs):
        """
        Make an HTTP DELETE request to the server.

        .. code-block:: python

            #example call
            try {
                headers, body = http.delete('/volumes/%s' % name)
            } except exceptions.HTTPUnauthorized as ex:
                print "Not logged in"
            }

        :param url: The relative url from the 3PAR api_url
        :type url: str

        :returns: headers - dict of HTTP Response headers
        :returns: body - the body of the response.  If the body was JSON, it
                         will be an object
        """
        return self._cs_request(url, 'DELETE', **kwargs)

