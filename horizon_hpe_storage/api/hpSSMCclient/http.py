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

import logging

try:
    import json
except ImportError:
    import simplejson as json

from horizon_hpe_storage.api.common import exceptions
from horizon_hpe_storage.api.common import http

LOG = logging.getLogger(__name__)


class HTTPJSONRESTClient(http.HTTPJSONRESTClient):
    """
    HTTP/REST client to access SSMC backend service
    """

    def authenticateSSMC(self, user, password, token, optional=None):
        """
        This tries to create an authenticated session with the
        HPE3PAR SSMC service

        :param user: The username
        :type user: str
        :param password: Password
        :type password: str

        """
        try:
            # this prevents re-auth attempt if auth fails
            self.auth_try = 1
            self.session_key = None

            # first check if old token is still valid
            if token is not None:
                LOG.info("####### 1-check if SSMC Token is valid: %s\n", token)
                header = {'Authorization': token}
                try:
                    resp, body = self.get(
                        '/foundation/REST/sessionservice/sessions/' +
                        token + '/context',
                        headers=header)
                    LOG.info("####### 2-SSMC Token is valid: %s\n", token)
                    self.auth_try = 0
                    self.user = user
                    self.password = password
                    self.session_key = token
                    return
                except Exception as ex:
                    # token has expired
                    token = None

            info = {'username': user,
                    'password': password,
                    'adminLogin': False,
                    'authLoginDomain': 'LOCAL'}
            self._auth_optional = None

            if optional:
                self._auth_optional = optional
                info.update(optional)

            LOG.info("####### 3-request new token\n")
            resp, body = self.post('/foundation/REST/sessionservice/sessions',
                                   body=info)
            if body and 'object' in body:
                object = body['object']
                if object and 'Authorization' in object:
                    self.session_key = object['Authorization']

            if self.session_key:
                LOG.info("####### 4-our new token: %s\n", self.session_key)
            else:
                LOG.info("####### 4-our new token: NONE\n")

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
        path = \
            '/provisioning/REST/volumeviewservice/volumes?query=name+eq+' + nn
        resp, body = self.get(path, headers=info)
        if body and 'count' in body:
            count = body['count']
            if count > 0:
                if 'members' in body:
                    members = body['members']
                    member = members[0]
                    if member:
                        if 'links' in member:
                            # store off link to this volume
                            links = member['links']
                            self_link = links[0]
                            if self_link and 'href' in self_link:
                                self.href = self_link['href']
                        if 'systemWWN' in member:
                            # store off link to array WWN for this volume
                            self.systemWWN = member['systemWWN']
                        if 'userCpgUid' in member:
                            # store off link to CPG for this volume
                            self.cpg = member['userCpgUid']
                        if 'domainUID' in member:
                            # store off link to Domain for this volume
                            self.domain = member['domainUID']

    def getCGroupLink(self, name):
        self.auth_try = 1
        info = {'Authorization': self.session_key}
        nn = "'%s'" % name
        path = \
            '/provisioning/REST/volumesetviewservice/sets?query=name+eq+' + nn
        resp, body = self.get(path, headers=info)
        if body and 'count' in body:
            count = body['count']
            if count > 0:
                if 'members' in body:
                    members = body['members']
                    member = members[0]
                    if member:
                        if 'links' in member:
                            # store off link to this volume
                            links = member['links']
                            for link in links:
                                if link['rel'] == "self":
                                    self.href = link['href']
                                    break

    # NOT NEEDED???
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

    def getVolumeCPG(self):
        return self.cpg

    def getVolumeDomain(self):
        return self.domain

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
            self.delete(
                '/foundation/REST/sessionservice/sessions/%s' %
                self.session_key)
            self.session_key = None
        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to log-off SSMC.'))
