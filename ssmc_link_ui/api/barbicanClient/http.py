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

from ssmc_link_ui.api.common import exceptions
from ssmc_link_ui.api.common import http


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

    def getSessionKey(self):
        return self.session_key

    def getSecretReference(self, token, host, type):
        # for right now, type = "-uname" or "-pwd"
        try:
            header = {'X-Auth-Token': token}
            resp, body = self.get('/v1/secrets?name=' + 'ssmc-' + host + type, headers=header)
            if body and 'total' in body:
                if body['total'] == 1:
                    if 'secrets' in body:
                        secrets = body['secrets']
                        secret = secrets[0]
                        sref = secret['secret_ref']
                        if sref is not None:
                            cnt = sref.find('/v1')
                            ref = sref[cnt:]
                            return ref

            return None

        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to get Barbican secret.'))

    def addSecret(self, token, host, secret, type):
        # for right now, type = "-uname" or "-pwd"
        self.auth_try = 1
        header = {'X-Auth-Token': token}
        try:
            # create secret
            info = {
                'name': 'ssmc-' + host + type,
                'payload': secret,
                'payload_content_type': 'text/plain',
                'secret_type': 'opaque'
            }
            resp, body = self.post('/v1/secrets', headers=header, body=info)
        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to add Barbican secret.'))

    def getCredentials(self, token, host):
        try:
            self.auth_try = 1
            pwd = None
            uname = None

            # get uname
            sref = self.getSecretReference(token, host, "-uname")
            if sref is not None:
                cnt = sref.find('/v1')
                ref = sref[cnt:]
                info = {'X-Auth-Token': token,
                        'Accept': 'text/plain'}
                resp, body = self.get(ref, headers=info)

                uname = body

            # get pwd
            sref = self.getSecretReference(token, host, "-pwd")
            if sref is not None:
                cnt = sref.find('/v1')
                ref = sref[cnt:]
                info = {'X-Auth-Token': token,
                        'Accept': 'text/plain'}
                resp, body = self.get(ref, headers=info)

                pwd = body

            return uname, pwd

        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to get Barbican credentials.'))

    def addCredentials(self, token, host, uname, pwd):
        self.auth_try = 1
        sref = None
        header = {'X-Auth-Token': token}
        try:
            # create secrets
            info = {
                'name': host + '-uname',
                'payload': uname,
                'payload_content_type': 'text/plain',
                'secret_type': 'opaque'
            }
            resp, body = self.post('/v1/secrets', headers=header, body=info)

            info = {
                'name': host + '-pwd',
                'payload': pwd,
                'payload_content_type': 'text/plain',
                'secret_type': 'opaque'
            }
            resp, body = self.post('/v1/secrets', headers=header, body=info)

        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to add Barbican credentials.'))

    def updateUserName(self, token, host, uname):
        # cannot modify secrets, so delete and then add
        ref = self.getSecretReference(token, host, '-uname')
        if ref:
            # delete secret
            header = {'X-Auth-Token': token}
            try:
                resp, body = self.delete(ref, headers=header)

                # add secret
                self.addSecret(token, host, uname, '-uname')
            except Exception as ex:
                exceptions.handle(self.request,
                                  ('Unable to update Barbican user name.'))

    def updatePassword(self, token, host, pwd):
        # cannot modify secrets, so delete and then add
        ref = self.getSecretReference(token, host, '-pwd')
        if ref:
            # delete secret
            header = {'X-Auth-Token': token}
            try:
                resp, body = self.delete(ref, headers=header)

                # add secret
                self.addSecret(token, host, pwd, '-pwd')
            except Exception as ex:
                exceptions.handle(self.request,
                                  ('Unable to update Barbican password.'))

    def deleteCredentials(self, token, host):
        try:
            self.auth_try = 1

            # get uname
            sref = self.getSecretReference(token, host, "-uname")
            if sref is not None:
                cnt = sref.find('/v1')
                ref = sref[cnt:]
                info = {'X-Auth-Token': token,
                        'Accept': 'text/plain'}
                resp, body = self.delete(ref, headers=info)

            # get pwd
            sref = self.getSecretReference(token, host, "-pwd")
            if sref is not None:
                cnt = sref.find('/v1')
                ref = sref[cnt:]
                info = {'X-Auth-Token': token,
                        'Accept': 'text/plain'}
                resp, body = self.delete(ref, headers=info)

            return None

        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to delete Barbican credentials.'))

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

