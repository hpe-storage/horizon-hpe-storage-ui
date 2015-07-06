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

try:
    import json
except ImportError:
    import simplejson as json

from ssmc_link_ui.api.common import exceptions
from ssmc_link_ui.api.common import http

LOG = logging.getLogger(__name__)

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

    def authenticateSSMC(self, user, password, token, optional=None):
        """
        This tries to create an authenticated session with the 3PAR server

        :param user: The username
        :type user: str
        :param password: Password
        :type password: str

        """
        try:
            # this prevens re-auth attempt if auth fails
            self.auth_try = 1
            self.session_key = None

            # first check if old token is still valid
            if token is not None:
                header = {'Authorization': token}
                resp, body = self.get('/foundation/REST/sessionservice/sessions/' + token + '/context', headers=header)
                if body and 'availableSystems' in body:
                    self.auth_try = 0
                    self.user = user
                    self.password = password
                    self.session_key = token
                    return

            info = {'username': user,
                    'password': password,
                    'adminLogin': False,
                    'authLoginDomain': 'LOCAL'}
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
            LOG.error("Unable to create SSMC Authorization Token: %s\n", body)
            self.session_key = None

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
        try:
            self.delete('/foundation/REST/sessionservice/sessions/%s' % self.session_key)
            self.session_key = None
        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to log-off SSMC.'))
