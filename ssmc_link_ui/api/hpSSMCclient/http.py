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

try:
    import json
except ImportError:
    import simplejson as json

from hp3parclient import exceptions


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

    def authenticateSSMC(self, user, password, token, optional=None):
        """
        This tries to create an authenticated session with the 3PAR server

        :param user: The username
        :type user: str
        :param password: Password
        :type password: str

        """
        try:
            # first check if old token is still valid
            if token is not None:
                header = {'Authorization': token}
                resp, body = self.get('/foundation/REST/sessionservice/sessions/' + token + '/context', headers=header)
                if body and 'availableSystems' in body:
                    self.user = user
                    self.password = password
                    self.session_key = token
                    return

            # this prevens re-auth attempt if auth fails
            self.auth_try = 1
            self.session_key = None

            info = {'username': user, 'password': password}
            self._auth_optional = None

            if optional:
                self._auth_optional = optional
                info.update(optional)

            resp, body = self.post('/foundation/REST/sessionservice/sessions', body=info)
            if body and 'object' in body:
                object = body['object']
                if object and 'Authorization' in object:
                    self.session_key = object['Authorization']

            self.auth_try = 0
            self.user = user
            self.password = password
        except Exception as ex:
            i = 10

    def getVolumeLink(self, name):
        self.auth_try = 1
        info = {'Authorization': self.session_key}
        nn = "'%s'" % name
        resp, body = self.get('/provisioning/REST/volumeviewservice/volumes?query=name+eq+' + nn, headers=info)
        # resp, body = self.get("/provisioning/REST/volumeviewservice/volumes?query=name")
        if body and 'count' in body:
            count = body['count']
            if count > 0:
                if 'members' in body:
                    members = body['members']
                    member = members[0]
                    if member and 'links' in member:
                        links = member['links']
                        self_link = links[0]
                        if self_link and 'href' in self_link:
                            self.href = self_link['href']

    def getVolumeDetails(self):
        self.auth_try = 1
        info = {'Authorization': self.session_key}
        cnt = self.href.find('/provisioning')
        ref = self.href[cnt:]
        resp, body = self.get(ref, headers=info)
        if body and 'uid' in body:
            self.uid = body['uid']
            if 'systemWWN' in body:
                self.systemWWN = body['systemWWN']

    def getSessionKey(self):
        return self.session_key

    def getVolumeRef(self):
        return self.href

    def getVolumeID(self):
        return self.uid

    def getSystemWWN(self):
        return self.systemWWN

    def _reauth(self):
        self.authenticateSSMC(self.user, self.password, self._auth_optional)

    def unauthenticateSSMC(self):
        """
        This clears the authenticated session with the 3PAR server.

        """
        # delete the session on the 3Par
        self.delete('/foundation/REST/sessionservice/sessions/%s' % self.session_key)
        self.session_key = None

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

