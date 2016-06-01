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

import base64
import uuid

from hpSSMCclient import client

import logging

LOG = logging.getLogger(__name__)

class HPSSMC(object):

    def __init__(self, endpt, username, password, token):
        self.client = None
        self.uuid = uuid.uuid4()
        self.ssmc_api_url = endpt
        self.ssmc_username = username
        self.ssmc_passwd = password
        self.ssmc_token = token
        self.ssmc_debug = True
        self.launch_page = self.ssmc_api_url + "#/launch-page/"
        self.showUrl = "/virtual-volumes/show/overview/r"

    def _create_client(self):
        cl = client.HPSSMCClient(self.ssmc_api_url)
        return cl

    def client_login(self):
        try:
            LOG.debug("Connecting to SSMC")
            self.client.login(self.ssmc_username,
                              self.ssmc_passwd,
                              self.ssmc_token)
        except Exception:
            LOG.error("Can't LOG IN")


    def client_logout(self):
        LOG.info(("Disconnect from SSMC REST %s") % self.uuid)
        self.client.logout()
        LOG.info(("logout Done %s") % self.uuid)

    def do_setup(self, context):
        try:
            self.client = self._create_client()
        except Exception:
            return
        if self.ssmc_debug:
            self.client.debug_rest(True)

    def _encode_name(self, name):
        """Get converted 3PAR volume name.

        Converts the openstack volume id from
        ecffc30f-98cb-4cf5-85ee-d7309cc17cd2
        to
        osv-7P.DD5jLTPWF7tcwnMF80g

        We convert the 128 bits of the uuid into a 24character long
        base64 encoded string to ensure we don't exceed the maximum
        allowed 31 character name limit on 3Par

        We strip the padding '=' and replace + with .
        and / with -
        """

        uuid_str = name.replace("-", "")
        vol_uuid = uuid.UUID('urn:uuid:%s' % uuid_str)
        vol_encoded = base64.b64encode(vol_uuid.bytes)

        # 3par doesn't allow +, nor /
        vol_encoded = vol_encoded.replace('+', '.')
        vol_encoded = vol_encoded.replace('/', '-')
        # strip off the == as 3par doesn't like those.
        vol_encoded = vol_encoded.replace('=', '')
        return vol_encoded

    def _get_3par_vol_name(self, volume_id):
        volume_name = self._encode_name(volume_id)
        LOG.info(("3PAR Volume Name: osv-%s") % volume_name)
        return "osv-%s" % volume_name

    def _get_3par_snapshot_name(self, snapshot_id):
        snapshot_name = self._encode_name(snapshot_id)
        LOG.info(("3PAR Volume Snapshot Name: oss-%s") % snapshot_name)
        return "oss-%s" % snapshot_name

    def get_session_token(self):
        LOG.debug("Requesting Token from SSMC")
        return self.client.getSessionSSMCToken(self.ssmc_username,
                                               self.ssmc_passwd)

    def get_snapshot_info(self, snapshot_id):
        LOG.debug("   TOKEN = " + self.client.getSessionKey())
        LOG.debug("Requesting SNAPSHOT LINK from SSMC")
        self.client.getVolumeLink(self._get_3par_snapshot_name(snapshot_id))
        LOG.debug("   href = " + self.client.getVolumeRef())

    def get_volume_info(self, volume_id):
        LOG.debug("   TOKEN = " + self.client.getSessionKey())
        LOG.debug("Requesting VOLUME LINK from SSMC")
        self.client.getVolumeLink(self._get_3par_vol_name(volume_id))
        LOG.debug("   href = " + self.client.getVolumeRef())

        # LOG.debug("Requesting VOLUME DETAILS from SSMC")
        # self.client.getVolumeDetails()
        # LOG.debug("   uuid = " + self.client.getVolumeID())
        # LOG.debug("   system WWN = " + self.client.getSystemWWN())

    def get_session_key(self):
        return self.client.getSessionKey()

    def get_volume_ref(self):
        return self.client.getVolumeRef()

    def get_volume_id(self):
        return self.client.getVolumeID()

    def get_system_wwn(self):
        return self.client.getSystemWWN()

    def get_volume_cpg(self):
        return self.client.getVolumeCPG()

    def get_volume_domain(self):
        return self.client.getVolumeDomain()
