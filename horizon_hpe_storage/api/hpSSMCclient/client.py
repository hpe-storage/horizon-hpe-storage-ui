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


class HPSSMCClient(object):

    """ Client layer to access HTTP calls to SSMC service.

    """

    def __init__(self, api_url):
        self.api_url = api_url
        self.http = http.HTTPJSONRESTClient(self.api_url)
        api_version = None

    def debug_rest(self, flag):
        """This is useful for debugging requests to 3PAR.

        :param flag: set to True to enable debugging
        :type flag: bool

        """
        self.http.set_debug_flag(flag)


    def login(self, username, password, token, optional=None):
        """This authenticates against the 3PAR wsapi server and creates a
           session.

        :param username: The username
        :type username: str
        :param password: The Password
        :type password: str

        :returns: None

        """
        self.http.authenticateSSMC(username, password, token, optional)

    def logout(self):
        """This destroys the session and logs out from the 3PAR server.
           The SSH connection to the 3PAR server is also closed.

        :returns: None

        """
        self.http.unauthenticateSSMC()

    def getSessionKey(self):
        return self.http.getSessionKey()

    def getVolumeLink(self, volume_name):
        return self.http.getVolumeLink(volume_name)

    def getVolumeDetails(self):
        return self.http.getVolumeDetails()

    def getVolumeRef(self):
        return self.http.getVolumeRef()

    def getVolumeCPG(self):
        return self.http.getVolumeCPG()

    def getVolumeDomain(self):
        return self.http.getVolumeDomain()

    def getVolumeID(self):
        return self.http.getVolumeID()

    def getSystemWWN(self):
        return self.http.getSystemWWN()

    def searchVolume(self, search):

        response, body = self.http.get(search)
        return body
