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

from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon.utils import memoized
from horizon import tabs

from openstack_dashboard.api import cinder

from horizon_hpe_storage.storage_panel.config import forms as config_forms
from horizon_hpe_storage.storage_panel import tabs as storage_tabs


import uuid
import base64
import re
import time
from urlparse import urlparse

import horizon_hpe_storage.api.hp_ssmc_api as hpssmc
import horizon_hpe_storage.api.keystone_api as keystone
import horizon_hpe_storage.api.barbican_api as barbican


import logging

LOG = logging.getLogger(__name__)


class IndexView(tabs.TabbedTableView):
    tab_group_class = storage_tabs.StorageTabs
    template_name = 'config/index.html'


class CreateEndpointView(forms.ModalFormView):
    form_class = config_forms.CreateEndpoint

    modal_header = _("Create Link")
    modal_id = "create_endpoint_modal"
    template_name = 'config/create_endpoint.html'
    submit_label = _("Create Link")
    submit_url = reverse_lazy(
        "horizon:admin:hpe_storage:config:create_endpoint")
    success_url = reverse_lazy('horizon:admin:hpe_storage:index')
    page_title = _("Create SSMC Link")


class EditEndpointView(forms.ModalFormView):
    form_class = config_forms.EditEndpoint
    modal_header = _("Edit Link")
    modal_id = "edit_endpoint_modal"
    template_name = 'config/edit_endpoint.html'
    submit_label = _("Edit Link")
    submit_url = "horizon:admin:hpe_storage:config:edit_endpoint"
    success_url = reverse_lazy('horizon:admin:hpe_storage:index')
    page_title = _("Edit SSMC Link")

    def get_context_data(self, **kwargs):
        context = super(EditEndpointView, self).get_context_data(**kwargs)
        args = (self.kwargs['service_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        service_id = self.kwargs['service_id']
        return {'service_id': service_id}


class BaseLinkView(forms.ModalFormView):
    form_class = config_forms.LinkToSSMC
    modal_header = _("Link to SSMC")
    modal_id = "link_to_SSMC_modal"
    template_name = 'config/link_and_launch.html'
    submit_label = _("Link")
    success_url = 'horizon:admin:volumes:volumes_tab'
    page_title = _("Linking to SSMC...")
    host = None
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()
    ssmc_api = None

    tokens = {}

    def get_cache_value(self, key):
        if key in self.tokens:
            return self.tokens[key]
        else:
            return None

    def get_SSMC_endpoint(self, volume, snapshot=None, getCGroup=False):
        self.keystone_api.do_setup(self.request)
        self.barbican_api.do_setup(self.keystone_api.get_session())

        host_name = getattr(volume, 'os-vol-host-attr:host', None)
        # pull out host from host name (comes between @ and #)
        found = re.search('@(.+?)#', host_name)
        if found:
            self.host = found.group(1)
        else:
            return None
        endpt = self.keystone_api.get_ssmc_endpoint_for_host(self.host)
        uname, pwd = self.barbican_api.get_ssmc_credentials(self.host)

        if endpt:
            # attempt to use previous token for the SSMC endpoint, if it exists
            ssmc_instance = urlparse(endpt).netloc
            ssmc_token = self.get_cache_value(
                'ssmc-link-' + ssmc_instance)
            ssmc_token_last_access_time = self.get_cache_value(
                'ssmc-link-timer-' + ssmc_instance)

            if ssmc_token:
                # SSMC tokens last for 15 minutes (default)
                # throw away token if older than 15 minutes since last access
                cur_time = time.time()
                session_timeout = 14 * 60 + 30     # 15 mins with fudge factor
                if (cur_time - ssmc_token_last_access_time) > session_timeout:
                    ssmc_token = None

            self.ssmc_api = hpssmc.HPSSMC(endpt, uname, pwd, ssmc_token)
            self.ssmc_api.do_setup(None)
            # this call is the bottle neck. Note that SSMC must attempt to
            # login to each of the arrays it manages. And if one of those is
            # down, the timeouts makes this call even longer to complete
            self.ssmc_api.client_login()

            if self.ssmc_api.get_session_key():
                if snapshot:
                    if volume.consistencygroup_id:
                        cgroup_id = volume.consistencygroup_id
                        self.ssmc_api.get_cgroup_info(cgroup_id)
                    else:
                        snapshot_id = getattr(snapshot, "id")
                        self.ssmc_api.get_snapshot_info(snapshot_id)
                elif getCGroup:
                    cgroup_id = volume.consistencygroup_id
                    self.ssmc_api.get_cgroup_info(cgroup_id)
                else:
                    volume_id = getattr(volume, "id")
                    self.ssmc_api.get_volume_info(volume_id)

                if not ssmc_token:
                    self.tokens['ssmc-link-' + ssmc_instance] = \
                        self.ssmc_api.get_session_key()
                    self.tokens['ssmc-link-timer-' + ssmc_instance] = \
                        time.time()

                return endpt
            else:
                cache.delete('ssmc-link-' + self.host)
                raise ValueError("Unable to login to HPE 3PAR SSMC")
        else:
            raise ValueError(
                "SSMC Endpoint does not exist for this backend host")

        return None

    def logout_SSMC_session(self):
        # logout of session
        self.ssmc_api.client_logout()
        cache.delete('ssmc-link-' + self.host)


class LinkVolumeView(BaseLinkView):
    submit_url = 'horizon:admin:hpe_storage:config:link_to_volume'

    def get_context_data(self, **kwargs):
        context = super(LinkVolumeView, self).get_context_data(**kwargs)
        args = (self.kwargs['volume_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        context['link_url'] = kwargs['form'].initial['link_url']
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            # from openstack_dashboard import policy
            # allowed = policy.check((("volume","volume:create"),),
            # self.request)
            volume_id = self.kwargs['volume_id']
            volume = cinder.volume_get(self.request, volume_id)

            # volume_name = self.get_3par_vol_name(volume_id)
            # LOG.info(("deep link - get keystone token for vol = %s") %
            # volume_name)
            # formatted_vol_name = format(volume_name)
            LOG.info(("deep link - get keystone token for vol = %s") %
                     volume.name)

            # get volume data to build URI to SSMC
            endpoint = self.get_SSMC_endpoint(volume)
            LOG.info(("deep-link - Session Token = %s") %
                     self.ssmc_api.get_session_key())

            if endpoint:
                # "0:url=" is needed for redirect tag for page
                # url = "0;url=" + endpoint + '#/virtual-volumes/show/'\
                #         'capacity/r/provisioning/REST/volumeviewservice/' \
                #         'systems/' + self.ssmc_api.get_system_wwn() + \
                #         '/volumes/' + self.ssmc_api.get_volume_id() + \
                #         '?sessionToken=' + self.ssmc_api.get_session_key()
                ref = urlparse(self.ssmc_api.get_volume_ref())
                url = "0;url=" + endpoint + \
                      '#/virtual-volumes/show/capacity/r' + \
                      ref.path + '?sessionToken=' + \
                      self.ssmc_api.get_session_key()

                # USE if we want user to log in every time
                # self.logout_SSMC_session()
                LOG.info(("deep-link - SSMC URL = %s") % url)
                return volume, url

        except ValueError as err:
            url = reverse('horizon:admin:volumes:volumes_tab')
            exceptions.handle(self.request,
                              err.message,
                              redirect=url)
        except Exception as err:
            LOG.info(("deep-link error = %s") % err.message)
            exceptions.handle(self.request,
                              _('Unable to retrieve volume details.'),
                              redirect=self.success_url)

    def get_initial(self):
        volume, link_url = self.get_data()
        return {'volume_id': self.kwargs["volume_id"],
                'name': volume.name,
                'link_url': link_url}


class LinkVolumeCPGView(BaseLinkView):
    submit_url = 'horizon:admin:hpe_storage:config:link_to_volume_cpg'

    def get_context_data(self, **kwargs):
        context = super(LinkVolumeCPGView, self).get_context_data(**kwargs)
        args = (self.kwargs['volume_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        context['link_url'] = kwargs['form'].initial['link_url']
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            # from openstack_dashboard import policy
            # allowed = policy.check((("volume","volume:create"),),
            # self.request)
            volume_id = self.kwargs['volume_id']
            volume = cinder.volume_get(self.request, volume_id)

            LOG.info(("deep link - get keystone token for vol = %s") %
                     volume.name)

            # get volume data to build URI to SSMC
            endpoint = self.get_SSMC_endpoint(volume)
            LOG.info(("deep-link - Session Token = %s") %
                     self.ssmc_api.get_session_key())
            if endpoint:
                # "0:url=" is needed for redirect tag for page
                url = "0;url=" + endpoint + '#/cpgs/show/'\
                      'overview/r/provisioning/REST/cpgviewservice/' \
                      'systems/' + self.ssmc_api.get_system_wwn() + \
                      '/cpgs/' + self.ssmc_api.get_volume_cpg() + \
                      '?sessionToken=' + self.ssmc_api.get_session_key()

                # USE if we want user to log in every time
                # self.logout_SSMC_session()
                LOG.info(("deep-link - SSMC URL = %s") % url)
                return volume, url

        except ValueError as err:
            url = reverse('horizon:admin:volumes:volumes_tab')
            exceptions.handle(self.request,
                              err.message,
                              redirect=url)
        except Exception as err:
            LOG.info(("deep-link error = %s") % err.message)
            exceptions.handle(self.request,
                              _('Unable to retrieve volume details.'),
                              redirect=self.success_url)

    def get_initial(self):
        volume, link_url = self.get_data()
        return {'volume_id': self.kwargs["volume_id"],
                'name': volume.name,
                'link_url': link_url}


class LinkVolumeDomainView(BaseLinkView):
    submit_url = 'horizon:admin:hpe_storage:config:link_to_volume_domain'

    def get_context_data(self, **kwargs):
        context = super(LinkVolumeDomainView, self).get_context_data(**kwargs)
        args = (self.kwargs['volume_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        context['link_url'] = kwargs['form'].initial['link_url']
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            # from openstack_dashboard import policy
            # allowed = policy.check((("volume","volume:create"),),
            # self.request)
            volume_id = self.kwargs['volume_id']
            volume = cinder.volume_get(self.request, volume_id)

            LOG.info(("deep link - get keystone token for vol = %s") %
                     volume.name)

            # get volume data to build URI to SSMC
            endpoint = self.get_SSMC_endpoint(volume)
            LOG.info(("deep-link - Session Token = %s") %
                     self.ssmc_api.get_session_key())
            if endpoint:
                # "0:url=" is needed for redirect tag for page
                url = "0;url=" + endpoint + '#/domains/show/' \
                      'overview/r/security/REST/domainviewservice/' \
                      'systems/' + self.ssmc_api.get_system_wwn() + \
                      '/domains/' + self.ssmc_api.get_volume_domain() + \
                      '?sessionToken=' + self.ssmc_api.get_session_key()

                # USE if we want user to log in every time
                # self.logout_SSMC_session()
                LOG.info(("deep-link - SSMC URL = %s") % url)
                return volume, url

        except ValueError as err:
            url = reverse('horizon:admin:volumes:volumes_tab')
            exceptions.handle(self.request,
                              err.message,
                              redirect=url)
        except Exception as err:
            LOG.info(("deep-link error = %s") % err.message)
            exceptions.handle(self.request,
                              _('Unable to retrieve volume details.'),
                              redirect=self.success_url)

    def get_initial(self):
        volume, link_url = self.get_data()
        return {'volume_id': self.kwargs["volume_id"],
                'name': volume.name,
                'link_url': link_url}


class LinkVolumeCGroupView(BaseLinkView):
    submit_url = 'horizon:admin:hpe_storage:config:link_to_volume_cgroup'

    def get_context_data(self, **kwargs):
        context = super(LinkVolumeCGroupView, self).get_context_data(**kwargs)
        args = (self.kwargs['volume_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        context['link_url'] = kwargs['form'].initial['link_url']
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            # from openstack_dashboard import policy
            # allowed = policy.check((("volume","volume:create"),),
            # self.request)
            volume_id = self.kwargs['volume_id']
            volume = cinder.volume_get(self.request, volume_id)

            LOG.info(("deep link - get keystone token for vol = %s") %
                     volume.name)

            # get volume data to build URI to SSMC
            endpoint = self.get_SSMC_endpoint(volume, getCGroup=True)
            LOG.info(("deep-link - Session Token = %s") %
                     self.ssmc_api.get_session_key())

            if endpoint:
                ref = urlparse(self.ssmc_api.get_volume_ref())

                # show vvset for cgroup
                url = "0;url=" + endpoint + \
                      '#/vv-sets/show/overview/r' + \
                      ref.path + '?sessionToken=' + \
                      self.ssmc_api.get_session_key()

                # USE if we want user to log in every time
                # self.logout_SSMC_session()
                LOG.info(("deep-link - SSMC URL = %s") % url)
                return volume, url

        except ValueError as err:
            url = reverse('horizon:admin:volumes:volumes_tab')
            exceptions.handle(self.request,
                              err.message,
                              redirect=url)
        except Exception as err:
            LOG.info(("deep-link error = %s") % err.message)
            exceptions.handle(self.request,
                              _('Unable to retrieve volume details.'),
                              redirect=self.success_url)

    def get_initial(self):
        volume, link_url = self.get_data()
        return {'volume_id': self.kwargs["volume_id"],
                'name': volume.name,
                'link_url': link_url}


class LinkSnapshotView(BaseLinkView):
    submit_url = 'horizon:admin:hpe_storage:config:link_to_snapshot'

    def get_context_data(self, **kwargs):
        context = super(LinkSnapshotView, self).get_context_data(**kwargs)
        args = (self.kwargs['snapshot_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        context['link_url'] = kwargs['form'].initial['link_url']
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            # from openstack_dashboard import policy
            # allowed = policy.check((("volume","volume:create"),),
            # self.request)
            snapshot_id = self.kwargs['snapshot_id']
            snapshot = cinder.volume_snapshot_get(self.request, snapshot_id)

            volume_id = snapshot.volume_id
            volume = cinder.volume_get(self.request, volume_id)

            LOG.info(("deep link - get keystone token for snapshot = %s") %
                     snapshot.name)

            # get volume data to build URI to SSMC
            endpoint = self.get_SSMC_endpoint(volume, snapshot)
            LOG.info(("deep-link - Session Token = %s") %
                     self.ssmc_api.get_session_key())

            if endpoint:
                ref = urlparse(self.ssmc_api.get_volume_ref())

                if volume.consistencygroup_id:
                    # show vvset for cgroup and let user navigate to snapshot
                    url = "0;url=" + endpoint + \
                          '#/vv-sets/show/overview/r' + \
                          ref.path + '?sessionToken=' + \
                          self.ssmc_api.get_session_key()
                else:
                    # show snapshot view
                    url = "0;url=" + endpoint + \
                          '#/virtual-volumes/show/capacity/r' + \
                          ref.path + '?sessionToken=' + \
                          self.ssmc_api.get_session_key()

                # USE if we want user to log in every time
                # self.logout_SSMC_session()
                LOG.info(("deep-link - SSMC URL = %s") % url)
                return snapshot, url

        except ValueError as err:
            url = reverse('horizon:admin:volumes:volumes_tab')
            exceptions.handle(self.request,
                              err.message,
                              redirect=url)
        except Exception as err:
            LOG.info(("deep-link error = %s") % err.message)
            exceptions.handle(self.request,
                              _('Unable to retrieve volume details.'),
                              redirect=self.success_url)

    def get_initial(self):
        snapshot, link_url = self.get_data()
        return {'snapshot_id': self.kwargs["snapshot_id"],
                'name': snapshot.name,
                'link_url': link_url}


class ValidateCinderView(forms.ModalFormView):
    form_class = config_forms.ValidateCinderNode
    modal_header = _("Validate SSH Credentials")
    modal_id = "validate_cinder_modal"
    template_name = 'config/validate_node.html'
    submit_label = _("Validate SSH Credentials")
    submit_url = "horizon:admin:hpe_storage:config:validate_cinder_node"
    success_url = reverse_lazy('horizon:admin:hpe_storage:index')
    page_title = _("Validate SSH Credentials")

    def get_context_data(self, **kwargs):
        context = super(ValidateCinderView, self).get_context_data(**kwargs)
        context["node_name"] = self.kwargs['node_name']
        args = (self.kwargs['node_name'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        node_name = self.kwargs['node_name']
        return {'node_name': node_name}


class ValidateAllCinderView(forms.ModalFormView):
    form_class = config_forms.ValidateAllCinderNodes
    modal_header = _("Validate SSH Credentials on All Cinder Nodes")
    modal_id = "validate_all_cinder_modal"
    template_name = 'config/validate_all_nodes.html'
    submit_label = _("Validate SSH Credentials")
    submit_url = reverse_lazy(
        "horizon:admin:hpe_storage:config:validate_all_cinder_nodes")
    success_url = 'horizon:admin:hpe_storage:index'
    page_title = _("Validate SSH Credentials")

    def get_success_url(self):
        return reverse(self.success_url)


class RegisterCinderView(forms.ModalFormView):
    form_class = config_forms.RegisterCinderNode
    modal_header = _("Register Cinder Node")
    modal_id = "register_cinder_modal"
    template_name = 'config/register_cinder.html'
    submit_label = _("Register Cinder Node")
    submit_url = reverse_lazy(
        "horizon:admin:hpe_storage:config:register_cinder_node")
    success_url = 'horizon:admin:hpe_storage:index'
    page_title = _("Register Cinder Node")

    def get_success_url(self):
        return reverse(self.success_url)


class EditCinderView(forms.ModalFormView):
    form_class = config_forms.EditCinderNode
    modal_header = _("Edit Cinder Node")
    modal_id = "edit_cinder_modal"
    template_name = 'config/edit_cinder.html'
    submit_label = _("Edit Cinder Node")
    submit_url = "horizon:admin:hpe_storage:config:edit_cinder_node"
    success_url = reverse_lazy('horizon:admin:hpe_storage:index')
    page_title = _("Edit Cinder Node")

    def get_context_data(self, **kwargs):
        context = super(EditCinderView, self).get_context_data(**kwargs)
        args = (self.kwargs['node_name'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        node_name = self.kwargs['node_name']
        return {'node_name': node_name}


class ValidateNovaView(forms.ModalFormView):
    form_class = config_forms.ValidateNovaNode
    modal_header = _("Validate SSH Credentials")
    modal_id = "validate_nova_modal"
    template_name = 'config/validate_node.html'
    submit_label = _("Validate SSH Credentials")
    submit_url = "horizon:admin:hpe_storage:config:validate_nova_node"
    success_url = reverse_lazy('horizon:admin:hpe_storage:index')
    page_title = _("Validate SSH Credentials")

    def get_context_data(self, **kwargs):
        context = super(ValidateNovaView, self).get_context_data(**kwargs)
        context["node_name"] = self.kwargs['node_name']
        args = (self.kwargs['node_name'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        node_name = self.kwargs['node_name']
        return {'node_name': node_name}


class ValidateAllNovaView(forms.ModalFormView):
    form_class = config_forms.ValidateAllNovaNodes
    modal_header = _("Validate SSH Credentials on All Nova Nodes")
    modal_id = "validate_all_nova_modal"
    template_name = 'config/validate_all_nodes.html'
    submit_label = _("Validate SSH Credentials")
    submit_url = reverse_lazy(
        "horizon:admin:hpe_storage:config:validate_all_nova_nodes")
    success_url = 'horizon:admin:hpe_storage:index'
    page_title = _("Validate SSH Credentials")

    def get_success_url(self):
        return reverse(self.success_url)


class RegisterNovaView(forms.ModalFormView):
    form_class = config_forms.RegisterNovaNode
    modal_header = _("Register Nova Node")
    modal_id = "create_nova_modal"
    template_name = 'config/register_nova.html'
    submit_label = _("Register Nova Node")
    submit_url = reverse_lazy(
        "horizon:admin:hpe_storage:config:register_nova_node")
    success_url = 'horizon:admin:hpe_storage:index'
    page_title = _("Register Nova Node")

    def get_success_url(self):
        return reverse(self.success_url)


class EditNovaView(forms.ModalFormView):
    form_class = config_forms.EditNovaNode
    modal_header = _("Edit Nova Node")
    modal_id = "edit_nova_modal"
    template_name = 'config/edit_nova.html'
    submit_label = _("Edit Nova Node")
    submit_url = "horizon:admin:hpe_storage:config:edit_nova_node"
    success_url = reverse_lazy('horizon:admin:hpe_storage:index')
    page_title = _("Edit Nova Node")

    def get_context_data(self, **kwargs):
        context = super(EditNovaView, self).get_context_data(**kwargs)
        args = (self.kwargs['node_name'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        node_name = self.kwargs['node_name']
        return {'node_name': node_name}
