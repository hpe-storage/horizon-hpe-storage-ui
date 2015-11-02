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
    # For Python 3.0 and later
    from urllib.parse import quote
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import quote

import http


class BarbicanClient(object):

    """ The 3PAR REST API Client.

    :param api_url: The url to the WSAPI service on 3PAR
                    ie. http://<3par server>:8080/api/v1
    :type api_url: str

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

    def getCredentials(self, token, host):
        return self.http.getCredentials(token, host)

    def addCredentials(self, token, host, uname, pwd):
        return self.http.addCredentials(token, host, uname, pwd)

    def updateUserName(self, token, host, uname):
        return self.http.updateUserName(token, host, uname)

    def updatePassword(self, token, host, pwd):
        return self.http.updatePassword(token, host, pwd)

    def deleteCredentials(self, token, host):
        return self.http.deleteCredentials(token, host)

    def addDiagTest(self, token, test_name, service_type, host_ip,
                    ssh_name, ssh_pwd, config_path, config_status=None,
                    software_status=None, run_time=None):
        return self.http.addDiagTest(token, test_name, service_type,
                                     host_ip, ssh_name, ssh_pwd,
                                     config_path, config_status,
                                     software_status, run_time)

    def getAllDiagTests(self, token):
        return self.http.getAllDiagTests(token)

    def getDiagTest(self, token, name):
        return self.http.getDiagTest(token, name)

    def deleteDiagTest(self, token, name):
        return self.http.deleteDiagTest(token, name)
