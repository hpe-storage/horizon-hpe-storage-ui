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

    def getSecret(self, token, ref):
        try:
            header = {'X-Auth-Token': token}
            resp, body = self.get('/v1/secrets/' + ref, headers=header)
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

            return body

        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to get Barbican secret by reference.'))

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

    def addSecret(self, token, name, secret):
        self.auth_try = 1
        header = {'X-Auth-Token': token}
        try:
            # create secret
            info = {
                'name': name,
                'payload': secret,
                'payload_content_type': 'text/plain',
                'secret_type': 'opaque'
            }
            resp, body = self.post('/v1/secrets', headers=header, body=info)
            return resp
        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to add Barbican secret.'))

    def addSSMCSecret(self, token, host, secret, type):
        # for right now, type = "-uname" or "-pwd"
        name = 'ssmc-' + host + type
        return self.addSecret(token, name, secret)

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
                self.addSSMCSecret(token, host, uname, '-uname')
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
                self.addSSMCSecret(token, host, pwd, '-pwd')
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

    def addDiagTest(self, token, test_name, service_type, host_ip,
                    ssh_name, ssh_pwd, config_path, config_status=None,
                    software_status=None, run_time=None):
        try:
            self.auth_try = 1
            header = {'X-Auth-Token': token}

            # first create secret for each field
            name_resp = self.addSecret(token, "test_name", test_name)
            type_resp = self.addSecret(token, "service_type", service_type)
            host_resp = self.addSecret(token, "host_ip", host_ip)
            ssh_name_resp = self.addSecret(token, "ssh_name", ssh_name)
            ssh_pwd_resp = self.addSecret(token, "ssh_pwd", ssh_pwd)
            config_resp = self.addSecret(token, "config_path", config_path)

            # create container
            info = {
                'name': 'cinderdiags-' + test_name,
                'type': 'generic',
                'secret_refs': [
                    { 'name': 'test_name',
                      'secret_ref': name_resp['location']
                    },
                    { 'name': 'service_type',
                      'secret_ref': type_resp['location']
                    },
                    { 'name': 'host_ip',
                      'secret_ref': host_resp['location']
                    },
                    { 'name': 'ssh_name',
                      'secret_ref': ssh_name_resp['location']
                    },
                    { 'name': 'ssh_pwd',
                      'secret_ref': ssh_pwd_resp['location']
                    },
                    { 'name': 'config_path',
                      'secret_ref': config_resp['location']
                    },
                ]
            }

            if config_status or software_status or run_time:
                srefs = info['secret_refs']
                if config_status:
                    status_resp = self.addSecret(token, "config_test_status", config_status)
                    data = {
                       'name': 'config_test_status',
                       'secret_ref': status_resp['location']
                    }
                    srefs.append(data)
                if software_status:
                    status_resp = self.addSecret(token, "software_test_status", software_status)
                    data = {
                       'name': 'software_test_status',
                       'secret_ref': status_resp['location']
                    }
                    srefs.append(data)
                if run_time:
                    run_time_resp = self.addSecret(token, "run_time", run_time)
                    data = {
                        'name': 'run_time',
                        'secret_ref': run_time_resp['location']
                    }
                    srefs.append(data)

            resp, body = self.post('/v1/containers', headers=header, body=info)

        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to create diag test in Barbican.'))

    def getAllDiagTests(self, token):
        try:
            self.auth_try = 1
            tests = []
            header = {'X-Auth-Token': token}
            resp, body = self.get('/v1/containers', headers=header)

            if body and 'containers' in body:
                containers = body['containers']
                # grab all containers that start with "cinderdiags-"
                for container in containers:
                    if container['name'].startswith('cinderdiags'):
                        testData = self.getDiagTest(token, container['name'])
                        tests.append(testData)

            return tests

        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to get Barbican containers.'))

    def getDiagTest(self, token, name):
        try:
            testData = {}
            testData['test_name'] = ''
            testData['service_type'] = ''
            testData['host_ip'] = ''
            testData['ssh_name'] = ''
            testData['ssh_pwd'] = ''
            testData['config_path'] = ''
            testData['config_test_status'] = ''
            testData['software_test_status'] = ''
            testData['run_time'] = ''
            self.auth_try = 1
            header = {'X-Auth-Token': token}
            resp, body = self.get('/v1/containers?name=' + name, headers=header)
            if body and 'total' in body:
                if body['total'] == 1:
                    if 'containers' in body:
                        containers = body['containers']
                        container = containers[0]
                        srefs = container['secret_refs']
                        info = {'X-Auth-Token': token,
                                'Accept': 'text/plain'}
                        for sref in srefs:
                            secret_ref = sref['secret_ref']
                            cnt = secret_ref.find('/v1/secrets')
                            ref = secret_ref[cnt:]
                            resp, body = self.get(ref, headers=info)
                            if sref['name'] == 'test_name':
                                testData['test_name'] = body
                            if sref['name'] == 'service_type':
                                testData['service_type'] = body
                            elif sref['name'] == 'host_ip':
                                testData['host_ip'] = body
                            elif sref['name'] == 'ssh_name':
                                testData['ssh_name'] = body
                            elif sref['name'] == 'ssh_pwd':
                                testData['ssh_pwd'] = body
                            elif sref['name'] == 'config_path':
                                testData['config_path'] = body
                            elif sref['name'] == 'config_test_status':
                                testData['config_test_status'] = body
                            elif sref['name'] == 'software_test_status':
                                testData['software_test_status'] = body
                            elif sref['name'] == 'run_time':
                                testData['run_time'] = body

            return testData

        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to get Barbican container.'))

    def deleteDiagTest(self, token, name):
        try:
            self.auth_try = 1
            header = {'X-Auth-Token': token}
            info = {'X-Auth-Token': token,
                    'Accept': 'text/plain'}
            container_name = 'cinderdiags-' + name
            resp, body = self.get('/v1/containers?name=' + container_name, headers=header)
            if body and 'total' in body:
                if body['total'] == 1:
                    if 'containers' in body:
                        containers = body['containers']
                        container = containers[0]

                        # first delete all contained secrets
                        secret_refs = container['secret_refs']
                        for secret_ref in secret_refs:
                            sref = secret_ref['secret_ref']
                            cnt = sref.find('/v1')
                            ref = sref[cnt:]
                            resp, body = self.delete(ref, headers=info)

                        # now delete container
                        container_ref = container['container_ref']
                        cnt = container_ref.find('/v1/containers')
                        ref = container_ref[cnt:]
                        resp, body = self.delete(ref, headers=info)

        except Exception as ex:
            exceptions.handle(self.request,
                              ('Unable to update Barbican container.'))

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

