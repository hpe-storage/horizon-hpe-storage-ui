# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon.utils import memoized
from openstack_dashboard.api import cinder

# from openstack_dashboard.api import cinder
from horizon_ssmc_link.storage_panel import forms as deeplink_forms

# from deep_link_ui import forms as xxx

from horizon import tabs
from openstack_dashboard.dashboards.admin.defaults import tabs as project_tabs

from horizon import tables
from horizon import tabs

import uuid
import base64
import re
from urlparse import urlparse

import horizon_ssmc_link.api.hp_ssmc_api as hpssmc
import horizon_ssmc_link.api.keystone_api as keystone
import horizon_ssmc_link.api.barbican_api as barbican

from horizon_ssmc_link.storage_panel import tables as project_tables
from horizon_ssmc_link.storage_panel import tabs as project_tabs

import logging

LOG = logging.getLogger(__name__)


class IndexView(tabs.TabbedTableView):
    tab_group_class = project_tabs.StorageTabs
    template_name = 'index.html'
    page_title = _("HP Storage")


class CreateEndpointView(forms.ModalFormView):
    form_class = deeplink_forms.CreateEndpoint

    modal_header = _("Create Endpoint")
    modal_id = "create_endpoint_modal"
    template_name = 'create_endpoint.html'
    submit_label = _("Create Endpoint")
    submit_url = reverse_lazy("horizon:admin:ssmc_link:create_endpoint")
    success_url = 'horizon:admin:ssmc_link:index'
    page_title = _("Create an Endpoint")

    def get_success_url(self):
        return reverse(self.success_url)


class EditEndpointView(forms.ModalFormView):
    form_class = deeplink_forms.EditEndpoint
    modal_header = _("Edit Endpoint")
    modal_id = "edit_endpoint_modal"
    template_name = 'edit_endpoint.html'
    submit_label = _("Edit Endpoint")
    submit_url = "horizon:admin:ssmc_link:edit_endpoint"
    success_url = 'horizon:admin:ssmc_link:index'
    page_title = _("Edit an Endpoint")

    def get_context_data(self, **kwargs):
        context = super(EditEndpointView, self).get_context_data(**kwargs)
        args = (self.kwargs['service_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_success_url(self):
        return reverse(self.success_url)

    @memoized.memoized_method
    def get_object(self, *args, **kwargs):
        qos_spec_id = self.kwargs['service_id']
        try:
            # self._object = api.cinder.qos_spec_get(self.request, qos_spec_id)
            i = 0
        except Exception as ex:
            msg = _('Unable to retrieve QoS Spec details.')
            exceptions.handle(self.request, msg)
        return self._object

    def get_initial(self):
        service_id = self.kwargs['service_id']
        return {'service_id': service_id}


ssmc_tokens = {}     # keep tokens for performance

class LinkView(forms.ModalFormView):
    form_class = deeplink_forms.LinkToSSMC
    modal_header = _("Link to SSMC")
    modal_id = "link_to_SSMC_modal"
    template_name = 'link_and_launch.html'
    submit_label = _("Link")
    submit_url = 'horizon:admin:ssmc_link:link_to'
    success_url = 'horizon:admin:volumes:volumes_tab'
    page_title = _("Linking to SSMC...")
    keystone_api = None
    barbican_api = None
    ssmc_api = None

    def get_context_data(self, **kwargs):
        context = super(LinkView, self).get_context_data(**kwargs)
        args = (self.kwargs['volume_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        context['link_url'] = kwargs['form'].initial['link_url']
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            # from openstack_dashboard import policy
            # allowed = policy.check((("volume","volume:create"),), self.request)
            # allowed = policy.check((("volume","volume:crXXeate"),), self.request)
            volume_id = self.kwargs['volume_id']
            volume = cinder.volume_get(self.request, volume_id)

            volume_name = self.get_3par_vol_name(volume_id)
            LOG.info(("!!!!!!!!!! GET ELEMENT MANAGER FOR VOLUME = %s") % volume_name)
            formatted_vol_name = format(volume_name)

            # get volume data to build URI to SSMC
            endpoint = self.get_SSMC_endpoint(volume)
            LOG.info(("Session Token = %s") % self.ssmc_api.get_session_key())
            if endpoint:
                # "0:url=" is needed for redirect tag for page
                url = "0;url=" + endpoint + '#/virtual-volumes/show/'\
                        'overview/r/provisioning/REST/volumeviewservice/' \
                        'systems/' + self.ssmc_api.get_system_wwn() + \
                        '/volumes/' + self.ssmc_api.get_volume_id() + \
                        '?sessionToken=' + self.ssmc_api.get_session_key()

                # USE if we want user to log in every time
                # self.logout_SSMC_session(endpoint)
                LOG.info(("SSMC URL = %s") % url)
                return volume, url

        except ValueError as err:
            url = reverse('horizon:admin:volumes:volumes_tab')
            exceptions.handle(self.request,
                              err.message,
                              redirect=url)
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve volume details.'),
                              redirect=self.success_url)

    def get_initial(self):
        volume, link_url = self.get_data()
        return {'volume_id': self.kwargs["volume_id"],
                'name': volume.name,
                'link_url': link_url}

    def get_3par_vol_name(self, id):
        uuid_str = id.replace("-", "")
        vol_uuid = uuid.UUID('urn:uuid:%s' % uuid_str)
        vol_encoded = base64.b64encode(vol_uuid.bytes)

        # 3par doesn't allow +, nor /
        vol_encoded = vol_encoded.replace('+', '.')
        vol_encoded = vol_encoded.replace('/', '-')
        # strip off the == as 3par doesn't like those.
        vol_encoded = vol_encoded.replace('=', '')
        return "osv-%s" % vol_encoded

    def get_SSMC_endpoint(self, volume):
        if self.keystone_api == None:
            self.keystone_api = keystone.KeystoneAPI()
            self.keystone_api.do_setup(None)
            self.keystone_api.client_login()

        host_name = getattr(volume, 'os-vol-host-attr:host', None)
        # pull out host from host name (comes between @ and #)
        found = re.search('@(.+?)#', host_name)
        if found:
            host = found.group(1)
        else:
            return None
        endpt = self.keystone_api.get_ssmc_endpoint_for_host(host)

        if self.barbican_api == None:
            self.barbican_api = barbican.BarbicanAPI()
            self.barbican_api.do_setup(None)
            # barbican_api.client_login()
        uname, pwd = self.barbican_api.get_credentials(self.keystone_api.get_session_key(),
                                                  host)

        if endpt:
            # attempt to use previous token for the SSMC endpoint, if it exists
            global ssmc_tokens
            ssmc_token = None
            # pull ip out of SSMC endpoint
            parsed = urlparse(endpt)
            ssmc_ip = parsed.hostname
            if ssmc_ip in ssmc_tokens:
                ssmc_token = ssmc_tokens[ssmc_ip]

            self.ssmc_api = hpssmc.HPSSMC(endpt, uname, pwd, ssmc_token)
            self.ssmc_api.do_setup(None)
            # this call is the bottle neck. Note that SSMC must attempt to
            # login to each of the arrays it manages. And if one of those is
            # down, the timeouts makes this call even longer to complete
            self.ssmc_api.client_login()

            if self.ssmc_api.get_session_key():
                self.ssmc_api.get_volume_info(volume.id)
                ssmc_tokens[ssmc_ip] = self.ssmc_api.get_session_key()
                return endpt
            else:
                raise ValueError("Unable to login to SSMC")
        else:
            raise ValueError("SSMC Endpoint does not exist for this backend host")

        return None

    def logout_SSMC_session(self, endpt):
        # logout of session
        self.ssmc_api.client_logout()

        global ssmc_tokens
        ssmc_token = None
        # pull ip out of SSMC endpoint
        parsed = urlparse(endpt)
        ssmc_ip = parsed.hostname
        if ssmc_ip in ssmc_tokens:
            # remove reference to this token, so we start fresh next time
            del ssmc_tokens[ssmc_ip]

