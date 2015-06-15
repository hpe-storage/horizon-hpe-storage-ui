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

# def get_SSMC_volume_data():
#     href = ssmc_api.get_SSMC_volume_link(token)
#

# def get_element_manager(volume):
#     """ Figure out which element manager correlates to the given
#         volume.
#         In this simple example, launch latest SSMC with a search on the
#         volume name.  In a real implementation, we might query keystone to
#         find the relevant endpoint to call
#     """
#     LOG.info(("!!!!!!!!!! GET ELEMENT MANAGER FOR VOLUME = %s") % volume.name)
#     volume_name = get_3par_vol_name(volume.id)
#     formatted_vol_name = format(volume_name)
#
#     # get volume data to build URI to SSMC
#     get_SSMC_volume_info(volume)
#     LOG.info(("Session Token = %s") % ssmc_api.get_session_key())
#
#     url = 'https://16.93.118.180:8443/#/virtual-volumes/show/'\
#             'overview/r/provisioning/REST/volumeviewservice/' \
#             'systems/' + ssmc_api.get_system_wwn() + \
#             '/volumes/' + ssmc_api.get_volume_id() + \
#             '?sessionToken=' + ssmc_api.get_session_key()
#
#     LOG.info(("SSMC URL = %s") % url)
#     return url

# class LaunchElementManager(tables.LinkAction):
#     """ Define a new action that launches an element manager
#     """
#     LOG.info(("!!!!!!!!!! LAUNCH ELEMENT MANAGER CALLED"))
#     # name = "deep_link"
#     verbose_name = _("Launch Element Manager")
#     policy_rules = (("volume", "admin_api"),)
#     # url = "horizon:admin:volumes:volume_types:create_type"
#
#     def get_link_url(self, volume):
#         return get_element_manager(volume)


# class LaunchElementManager2(tables.Action):
#     LOG.info(("!!!!!!!!!! LAUNCH ELEMENT MANAGER 222 CALLED"))
#     name = "link_to"
#     verbose_name = _("Link to Volume")
#     url = "horizon:admin:volumes:volumes:link_toz"
#     classes = ("ajax-modal",)
#     icon = "plus"
#     policy_rules = (("volume", "volume_extension:volume_manage"),)
#     ajax = True
#
#     def single(self, data_table, request, volume_id):
#         volume = None
#         for row in data_table.data:
#             if row.id == volume_id:
#                 volume = row
#                 break
#
#         if volume is not None:
#             ssmc_url = get_element_manager(volume)
#             webbrowser.open_new_tab(ssmc_url)


class LaunchElementManager3(tables.LinkAction):
    LOG.info(("!!!!!!!!!! LAUNCH ELEMENT MANAGER 777777777 CALLED"))
    name = "link_to"
    verbose_name = _("Link to Volume")
    # url = "horizon:admin:volumes:volumes:update_status"
    # url = "horizon:admin:volumes:volumes:link_to"
    url = "horizon:admin:ssmc_link:link_to"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (("volume", "volume_extension:volume_manage"),)


class VolumesTableWithLaunch(volumes_tables.VolumesTable):
    """ Extend the VolumesTable by adding the new row action
    """
    # host = tables.Column("os-vol-host-attr:host",
    #                      link=get_element_manager,
    #                      verbose_name=_("Host"))

    class Meta(volumes_tables.VolumesTable.Meta):
        # Add the extra action to the end of the row actions
        row_actions = volumes_tables.VolumesTable.Meta.row_actions + \
                      (LaunchElementManager3,)


# Replace the standard Volumes table with this extended version
tabs.VolumeTab.table_classes = (VolumesTableWithLaunch,)

# admin_dashboard = horizon.get_dashboard("admin")
# vol_panel = admin_dashboard = admin_dashboard.get_panel("volumes")
# url_patterns = vol_panel._decorated_urls[0][4].url_patterns
# from django.conf.urls import url
# # from deep_link_ui.dashboards.admin.volumes import views
# # link_to_url = url(r'^(?P<volume_id>[^/]+)/link_to/$',
# #         views.LinkView.as_view(),
# #         name='link_to')
# from openstack_dashboard.dashboards.project.volumes \
#     .volumes import views
# link_to_url = url(r'^(?P<volume_id>[^/]+)/create_snapshot/$',
#         views.CreateSnapshotView.as_view(),
#         name='link_to')
# url_patterns.append(link_to_url)





