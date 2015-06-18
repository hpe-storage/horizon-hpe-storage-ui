#
# This is an example of how to contribute to an existing horizon page
#
from django.utils.translation import ugettext_lazy as _
from horizon import tables
from openstack_dashboard.dashboards.admin.volumes.volumes import tables \
    as volumes_tables
from openstack_dashboard.dashboards.admin.volumes import tabs

from django.core.urlresolvers import reverse

import base64
import horizon
import uuid
import webbrowser

import api.hp_ssmc_api as hpssmc
import api.keystone_api as keystone
import api.barbican_api as barbican

import logging

LOG = logging.getLogger(__name__)

ssmc_api = None
barbican_api = None

def get_3par_vol_name(id):
    uuid_str = id.replace("-", "")
    vol_uuid = uuid.UUID('urn:uuid:%s' % uuid_str)
    vol_encoded = base64.b64encode(vol_uuid.bytes)

    # 3par doesn't allow +, nor /
    vol_encoded = vol_encoded.replace('+', '.')
    vol_encoded = vol_encoded.replace('/', '-')
    # strip off the == as 3par doesn't like those.
    vol_encoded = vol_encoded.replace('=', '')
    return "osv-%s" % vol_encoded

def get_SSMC_volume_info(volume):
    global keystone_api
    keystone_api = keystone.KeystoneAPI()
    keystone_api.do_setup(None)
    keystone_api.client_login()
    endpt = keystone_api.get_ssmc_endpoint(volume)

    global barbican_api
    barbican_api = barbican.BarbicanAPI()
    barbican_api.do_setup(None)
    # barbican_api.client_login()
    uname, pwd = barbican_api.get_credentials(keystone_api.get_session_key(),
                                              '3parfc')

    global ssmc_api
    ssmc_api = hpssmc.HPSSMC(endpt, uname, pwd)
    ssmc_api.do_setup(None)
    ssmc_api.client_login()

    ssmc_api.get_volume_info(volume.id)


class LaunchElementManager(tables.LinkAction):
    LOG.info(("!!!!!!!!!! LAUNCH ELEMENT MANAGER CALLED"))
    verbose_name = _("Link to Volume")
    url = "horizon:admin:ssmc_link:link_to"

    # launch in new window
    attrs = {"target": "_blank"}

    # policy_rules = (("volume", "volume_extension:volume_manage"),)

    def get_link_url(self, volume):
        link_url = reverse(self.url, args=[volume.id])
        return link_url


class VolumesTableWithLaunch(volumes_tables.VolumesTable):
    """ Extend the VolumesTable by adding the new row action
    """
    class Meta(volumes_tables.VolumesTable.Meta):
        # Add the extra action to the end of the row actions
        row_actions = volumes_tables.VolumesTable.Meta.row_actions + \
                      (LaunchElementManager,)



# Replace the standard Volumes table with this extended version
tabs.VolumeTab.table_classes = (VolumesTableWithLaunch,)





