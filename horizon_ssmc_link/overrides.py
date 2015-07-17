#
# This is an example of how to contribute to an existing horizon page
#
from django.utils.translation import ugettext_lazy as _
from horizon import tables
from openstack_dashboard.dashboards.admin.volumes.volumes import tables \
    as volumes_tables
from openstack_dashboard.dashboards.admin.volumes import tabs

from django.core.urlresolvers import reverse

import logging

LOG = logging.getLogger(__name__)


class LaunchElementManagerVolume(tables.LinkAction):
    LOG.info(("!!!!!!!!!! LAUNCH ELEMENT MANAGER VOLUME CALLED"))
    name = "link_volume"
    verbose_name = _("View Volume in HP 3PAR SSMC")
    url = "horizon:admin:ssmc_link:link_to_volume"

    # launch in new window
    attrs = {"target": "_blank"}

    policy_rules = (("volume", "volume:deep_link"),)

    def get_link_url(self, volume):
        link_url = reverse(self.url, args=[volume.id])
        return link_url


class LaunchElementManagerCPG(tables.LinkAction):
    LOG.info(("!!!!!!!!!! LAUNCH ELEMENT MANAGER CPG CALLED"))
    name = "link_cpg"
    verbose_name = _("View Volume CPG in HP 3PAR SSMC")
    url = "horizon:admin:ssmc_link:link_to_cpg"

    # launch in new window
    attrs = {"target": "_blank"}

    policy_rules = (("volume", "volume:deep_link"),)

    def get_link_url(self, volume):
        link_url = reverse(self.url, args=[volume.id])
        return link_url


class LaunchElementManagerDomain(tables.LinkAction):
    LOG.info(("!!!!!!!!!! LAUNCH ELEMENT MANAGER DOMAIN CALLED"))
    name = "link_domain"
    verbose_name = _("View Volume Domain in HP 3PAR SSMC")
    url = "horizon:admin:ssmc_link:link_to_domain"

    # launch in new window
    attrs = {"target": "_blank"}

    policy_rules = (("volume", "volume:deep_link"),)

    def get_link_url(self, volume):
        link_url = reverse(self.url, args=[volume.id])
        return link_url


class VolumesTableWithLaunch(volumes_tables.VolumesTable):
    """ Extend the VolumesTable by adding the new row action
    """
    class Meta(volumes_tables.VolumesTable.Meta):
        # Add the extra action to the end of the row actions
        row_actions = volumes_tables.VolumesTable.Meta.row_actions + \
                      (LaunchElementManagerVolume,
                       LaunchElementManagerCPG,
                       LaunchElementManagerDomain)

# Replace the standard Volumes table with this extended version
tabs.VolumeTab.table_classes = (VolumesTableWithLaunch,)





