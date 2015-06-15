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
from ssmc_link_ui import forms as deeplink_forms

# from deep_link_ui import forms as xxx

from horizon import tabs
from openstack_dashboard.dashboards.admin.defaults import tabs as project_tabs

from horizon import tables
import uuid
import base64
import re

import api.hp_ssmc_api as hpssmc
import api.keystone_api as keystone
import api.barbican_api as barbican

from ssmc_link_ui import tables as project_tables

import logging

LOG = logging.getLogger(__name__)


class IndexView(tables.DataTableView):
    table_class = project_tables.EndpointsTable
    template_name = 'index.html'
    page_title = _("Link Backends to SSMC Endpoints")

    def get_data(self):
        endpoints = []

        try:
            keystone_api = keystone.KeystoneAPI()
            keystone_api.do_setup(None)
            keystone_api.client_login()
            endpoints = keystone_api.get_ssmc_endpoints()

            # for each endpoint, get credentials
            barbican_api = barbican.BarbicanAPI()
            barbican_api.do_setup(None)
            for endpoint in endpoints:
                uname, pwd = barbican_api.get_credentials(
                    keystone_api.get_session_key(), endpoint['backend'])
                endpoint['username'] = uname

        except Exception:
            msg = _('Unable to retrieve endpoints list.')
            exceptions.handle(self.request, msg)
        return endpoints


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


class LinkView(forms.ModalFormView):
    form_class = deeplink_forms.LinkToSSMC
    modal_header = _("Link to SSMC")
    modal_id = "link_to_SSMC_modal"
    template_name = 'link_and_launch.html'
    submit_label = _("Link")
    submit_url = 'horizon:admin:ssmc_link:link_to'
    success_url = 'horizon:admin:volumes:volumes_tab'
    page_title = _("Link To SSMC")

    def get_context_data(self, **kwargs):
        context = super(LinkView, self).get_context_data(**kwargs)
        args = (self.kwargs['volume_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        context['link_url'] = kwargs['form'].initial['link_url']
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            volume_id = self.kwargs['volume_id']
            volume = cinder.volume_get(self.request, volume_id)
            volume_name = self.get_3par_vol_name(volume_id)
            LOG.info(("!!!!!!!!!! GET ELEMENT MANAGER FOR VOLUME = %s") % volume_name)
            formatted_vol_name = format(volume_name)

            # get volume data to build URI to SSMC
            endpoint = self.get_SSMC_endpoint(volume)
            LOG.info(("Session Token = %s") % ssmc_api.get_session_key())

            if endpoint:
                url = endpoint + '#/virtual-volumes/show/'\
                        'overview/r/provisioning/REST/volumeviewservice/' \
                        'systems/' + ssmc_api.get_system_wwn() + \
                        '/volumes/' + ssmc_api.get_volume_id() + \
                        '?sessionToken=' + ssmc_api.get_session_key()

                LOG.info(("SSMC URL = %s") % url)
                return volume, url

        except ValueError as err:
            exceptions.handle(self.request,
                              err.message,
                              redirect=self.success_url)
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
        global keystone_api
        keystone_api = keystone.KeystoneAPI()
        keystone_api.do_setup(None)
        keystone_api.client_login()
        host_name = getattr(volume, 'os-vol-host-attr:host', None)
        # pull out host from host name (comes between @ and #)
        found = re.search('@(.+?)#', host_name)
        if found:
            host = found.group(1)
        else:
            return None
        endpt = keystone_api.get_ssmc_endpoint_for_host(host)

        global barbican_api
        barbican_api = barbican.BarbicanAPI()
        barbican_api.do_setup(None)
        # barbican_api.client_login()
        uname, pwd = barbican_api.get_credentials(keystone_api.get_session_key(),
                                                  host)

        global ssmc_api
        if endpt:
            ssmc_api = hpssmc.HPSSMC(endpt, uname, pwd)
            ssmc_api.do_setup(None)
            ssmc_api.client_login()

            ssmc_api.get_volume_info(volume.id)
            return endpt
        else:
            raise ValueError("SSMC Endpoint does not exist for this backend host")

        return None
