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

from django.core.exceptions import ValidationError  # noqa
from django.core.urlresolvers import reverse
from django.template import defaultfilters as filters
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from openstack_auth import utils as auth_utils

from horizon import exceptions
from horizon import forms
from horizon import tables
from keystoneclient.exceptions import Conflict  # noqa

from openstack_dashboard import api
from openstack_dashboard import policy

import ssmc_link_ui.api.keystone_api as keystone
import ssmc_link_ui.api.barbican_api as barbican


class CreateEndpointAction(tables.LinkAction):
    name = "create_endpoint"
    verbose_name = _("Create Endpoint")
    url = "horizon:admin:ssmc_link:create_endpoint"
    classes = ("ajax-modal",)
    icon = "plus"


class EditEndpointAction(tables.LinkAction):
    name = "edit_endpoint"
    verbose_name = _("Edit Endpoint")
    url = "horizon:admin:ssmc_link:edit_endpoint"
    classes = ("ajax-modal",)
    icon = "pencil"


class DeleteEndpointAction(tables.DeleteAction):
    name = "delete_endpoint"

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Endpoint",
            u"Delete Endpoints",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Endpoint",
            u"Deleted Endpoints",
            count
        )

    def delete(self, request, service_id):
        keystone_api = keystone.KeystoneAPI()
        keystone_api.do_setup(None)
        keystone_api.client_login()
        host = keystone_api.get_ssmc_service_name(service_id)
        backend = host[5:]    # remove 'ssmc-' prefix

        # first delete the credentials
        barbican_api = barbican.BarbicanAPI()
        barbican_api.do_setup(None)
        barbican_api.delete_credentials(keystone_api.get_session_key(),
                                        backend)

        # now delete service and endpoint
        keystone_api.delete_ssmc_endpoint(service_id)


class EndpointsTable(tables.DataTable):
    cinder_backend = tables.Column('backend', verbose_name=_('Backend'),
                         form_field=forms.CharField(max_length=64))
    ssmc_endpoint = tables.Column('endpoint', verbose_name=_('SSMC Endpoint'),
                         form_field=forms.CharField(max_length=64))
    access = tables.Column('username', verbose_name=_('SSMC Login'),
                         form_field=forms.CharField(max_length=64))

    def get_object_display(self, endpoint):
        return endpoint['backend']

    def get_object_id(self, endpoint):
        return endpoint['id']

    class Meta(object):
        name = "deeplinks"
        verbose_name = _("Backend EndPoints")
        hidden_title = False
        table_actions = (CreateEndpointAction,
                         DeleteEndpointAction,)
        row_actions = (EditEndpointAction,
                       DeleteEndpointAction,)
