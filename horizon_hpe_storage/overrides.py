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

from django.utils.translation import ugettext_lazy as _
from horizon import tables
from openstack_dashboard.dashboards.admin.volumes.volumes import tables \
    as volumes_tables
from openstack_dashboard.dashboards.admin.volumes.snapshots import tables \
    as snapshots_tables
from openstack_dashboard.dashboards.admin.volumes import tabs

from django.core.urlresolvers import reverse

import logging
import re

import horizon_hpe_storage.api.keystone_api as keystone

LOG = logging.getLogger(__name__)

# save off keystone session so we don't have to retrieve it for
# every volume in the volume table
keystone_api = None


class VolumeBaseElementManager(tables.LinkAction):
    # launch in new window
    attrs = {"target": "_blank"}
    policy_rules = (("volume", "volume:deep_link"),)

    def get_link_url(self, volume):
        link_url = reverse(self.url, args=[volume.id])
        return link_url

    def get_deep_link_endpoints(self, request):
        global keystone_api
        endpoints = []
        for i in range(0, 2):
            try:
                if not keystone_api:
                    keystone_api = keystone.KeystoneAPI()
                    keystone_api.do_setup(request)

                endpoints = keystone_api.get_ssmc_endpoints()
                return endpoints
            except Exception as ex:
                # try again, as this may be due to expired keystone session
                keystone_api = None
                continue

        return endpoints

    def allowed(self, request, volume=None):
        # don't allow deep link option if volume is not tied
        # to an SSMC endpoint
        if volume:
            host = getattr(volume, 'os-vol-host-attr:host', None)
            # pull out host from host name (comes between @ and #)
            if host:
                found = re.search('@(.+?)#', host)
                if found:
                    backend = found.group(1)
                    endpoints = self.get_deep_link_endpoints(request)
                    for endpoint in endpoints:
                        if endpoint['backend'] == backend:
                            return True

        return False


class VolumeLaunchElementManagerVolume(VolumeBaseElementManager):
    LOG.info(("Deep Link - launch element manager volume"))
    name = "link_volume"
    verbose_name = _("View Volume in HPE 3PAR SSMC")
    url = "horizon:admin:hpe_storage:config:link_to_volume"


class VolumeLaunchElementManagerCPG(VolumeBaseElementManager):
    LOG.info(("Deep Link - launch element manager volume CPG"))
    name = "link_volume_cpg"
    verbose_name = _("View Volume CPG in HPE 3PAR SSMC")
    url = "horizon:admin:hpe_storage:config:link_to_volume_cpg"


class VolumeLaunchElementManagerDomain(VolumeBaseElementManager):
    LOG.info(("Deep Link - launch element manager volume domain"))
    name = "link_volume_domain"
    verbose_name = _("View Volume Domain in HPE 3PAR SSMC")
    url = "horizon:admin:hpe_storage:config:link_to_volume_domain"


class VolumeLaunchElementManagerCGroup(VolumeBaseElementManager):
    LOG.info(("Deep Link - launch element manager volume consistency group"))
    name = "link_volume_cgroup"
    verbose_name = _("View Volume Consistency Group in HPE 3PAR SSMC")
    url = "horizon:admin:hpe_storage:config:link_to_volume_cgroup"

    def allowed(self, request, volume=None):
        # only allow if this volume is associated
        # with a consistency group
        if volume:
            if volume.consistencygroup_id:
                return True

        return False


class VolumesTableWithLaunch(volumes_tables.VolumesTable):
    """ Extend the VolumesTable by adding the new row action
    """
    class Meta(volumes_tables.VolumesTable.Meta):
        # Add the extra action to the end of the row actions
        row_actions = volumes_tables.VolumesTable.Meta.row_actions + \
            (VolumeLaunchElementManagerVolume,
             VolumeLaunchElementManagerCPG,
             VolumeLaunchElementManagerDomain,
             VolumeLaunchElementManagerCGroup)


class SnapshotBaseElementManager(tables.LinkAction):
    # launch in new window
    attrs = {"target": "_blank"}
    policy_rules = (("volume", "volume:deep_link"),)

    def get_link_url(self, snapshot):
        link_url = reverse(self.url, args=[snapshot.id])
        return link_url

    def get_deep_link_endpoints(self, request):
        global keystone_api
        endpoints = []
        for i in range(0, 2):
            try:
                if not keystone_api:
                    keystone_api = keystone.KeystoneAPI()
                    keystone_api.do_setup(request)

                endpoints = keystone_api.get_ssmc_endpoints()
                return endpoints
            except Exception as ex:
                # try again, as this may be due to expired keystone session
                keystone_api = None
                continue

        return endpoints

    def allowed(self, request, snapshot=None):
        # don't allow deep link option if this snapshot
        # is associated with a consistency group (because we
        # can't determine the full 3PAR name)
        # if snapshot._volume.consistencygroup_id:
        #     return False

        # don't allow deep link option if snapshot is not tied
        # to an SSMC endpoint

        if snapshot.host_name:
            # pull out host from host name (comes between @ and #)
            found = re.search('@(.+?)#', snapshot.host_name)
            if found:
                backend = found.group(1)
                endpoints = self.get_deep_link_endpoints(request)
                for endpoint in endpoints:
                    if endpoint['backend'] == backend:
                        if snapshot._volume.consistencygroup_id:
                            # self.verbose_name = \
                            #     _("View Volume Consistency Group "
                            #       "in HPE 3PAR SSMC")
                            # REMOVE THIS OPTION FOR NOW - too confusing
                            # for to show user vvset and them have
                            # navigate to the snapshot
                            return False
                        else:
                            return True

        return False


class SnapshotLaunchElementManagerVolume(SnapshotBaseElementManager):
    LOG.info(("Deep Link - launch element manager snapshot"))
    name = "link_snapshot"
    verbose_name = _("View Snapshot in HPE 3PAR SSMC")
    url = "horizon:admin:hpe_storage:config:link_to_snapshot"


class SnapshotsTableWithLaunch(snapshots_tables.VolumeSnapshotsTable):
    """ Extend the VolumeSnapshotsTable by adding the new row action
    """
    class Meta(snapshots_tables.VolumeSnapshotsTable.Meta):
        # Add the extra action to the end of the row actions
        row_actions = \
            snapshots_tables.VolumeSnapshotsTable.Meta.row_actions + \
            (SnapshotLaunchElementManagerVolume,)


# Replace the standard Volumes table with this extended version
tabs.VolumeTab.table_classes = (VolumesTableWithLaunch,)
# Replace the standard Volumes table with this extended version
tabs.SnapshotTab.table_classes = (SnapshotsTableWithLaunch,)
