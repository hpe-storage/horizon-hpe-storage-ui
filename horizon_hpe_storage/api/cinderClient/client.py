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


class CinderClient(object):

    """ Client layer to access HTTP calls to Cinder backend.

    This is needed due to limitations in current python-cinderclient API.
    Features not supported by python-cinderclient will be implemented here.

    """

    def __init__(self, api_url):
        self.api_url = api_url
        self.http = http.HTTPJSONRESTClient(self.api_url)
        api_version = None

    def debug_rest(self, flag):
        """This is useful for debugging requests to service.

        :param flag: set to True to enable debugging
        :type flag: bool

        """
        self.http.set_debug_flag(flag)


    def login(self, username, password, optional=None):
        """This authenticates against the service and creates a
           session.

        :param username: The username
        :type username: str
        :param password: The Password
        :type password: str

        :returns: None

        """
        self.http.authenticateKeystone(username, password, optional)

    def logout(self):
        """This destroys the session and logs out from the service.
           The SSH connection to the service is also closed.

        :returns: None

        """
        self.http.unauthenticateKeystone()


    def getHostCapabilities(self, token, tenant_id, host):
        return self.http.getHostCapabilities(token, tenant_id, host)
