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
from django.utils.translation import ungettext_lazy
from django.utils.translation import ugettext_lazy as _
from django.utils import safestring

from horizon import exceptions
from horizon import forms
from horizon import tables

import horizon_hpe_storage.api.keystone_api as keystone
import horizon_hpe_storage.api.barbican_api as barbican


class CreateEndpointAction(tables.LinkAction):
    name = "create_endpoint"
    verbose_name = _("Create Link")
    url = "horizon:admin:hpe_storage:config:create_endpoint"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (("volume", "volume:deep_link"),)


class EditEndpointAction(tables.LinkAction):
    name = "edit_endpoint"
    verbose_name = _("Edit Link")
    url = "horizon:admin:hpe_storage:config:edit_endpoint"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (("volume", "volume:deep_link"),)


class DeleteEndpointAction(tables.DeleteAction):
    name = "delete_endpoint"
    policy_rules = (("volume", "volume:deep_link"),)
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Link",
            u"Delete Links",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Link",
            u"Deleted Links",
            count
        )

    def delete(self, request, service_id):
        self.keystone_api.do_setup(request)
        self.barbican_api.do_setup(self.keystone_api.get_session())
        host = self.keystone_api.get_ssmc_service_name(service_id)
        backend = host[5:]    # remove 'ssmc-' prefix

        # first delete the credentials
        self.barbican_api.delete_ssmc_credentials(backend)

        # now delete service and endpoint
        self.keystone_api.delete_ssmc_endpoint(service_id)

        # cached SSMC token is no longer valid
        cache.delete('ssmc-link-' + host)


class EndpointsTable(tables.DataTable):
    cinder_backend = tables.Column(
        'backend',
        verbose_name=_('Cinder Backend'),
        form_field=forms.CharField(max_length=64))
    ssmc_endpoint = tables.Column(
        'endpoint',
        verbose_name=_('SSMC Instance'),
        form_field=forms.CharField(max_length=64))
    access = tables.Column(
        'username',
        verbose_name=_('SSMC Login'),
        form_field=forms.CharField(max_length=64))

    def get_object_display(self, endpoint):
        return endpoint['backend']

    def get_object_id(self, endpoint):
        return endpoint['id']

    class Meta(object):
        name = "endpoints"
        verbose_name = _("Deep Links Between Horizon Volumes and HPE SSMC")
        hidden_title = False
        table_actions = (CreateEndpointAction,
                         DeleteEndpointAction,)
        row_actions = (EditEndpointAction,
                       DeleteEndpointAction,)


class RegisterCinderAction(tables.LinkAction):
    name = "register_cinder_node"
    verbose_name = _("Register Cinder Node")
    url = "horizon:admin:hpe_storage:config:register_cinder_node"
    classes = ("ajax-modal",)
    icon = "plus"


class DeleteCinderAction(tables.DeleteAction):
    name = "cinder_delete"
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Cinder Node",
            u"Delete Cinder Nodes",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Cinder Node",
            u"Deleted Cinder Nodes",
            count
        )

    def delete(self, request, obj_id):
        try:
            self.keystone_api.do_setup(request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            self.barbican_api.delete_node(
                obj_id, barbican.CINDER_NODE_TYPE)
        except Exception as ex:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _('Unable to delete Cinder node registration'),
                              redirect=redirect)


class ValidateAllCinderAction(tables.LinkAction):
    name = "validate_all_cinder_nodes"
    verbose_name = _("Validate SSH Credentials on All Cinder Nodes")
    url = "horizon:admin:hpe_storage:config:validate_all_cinder_nodes"
    classes = ("ajax-modal",)
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def allowed(self, request, node=None):
        self.keystone_api.do_setup(request)
        self.barbican_api.do_setup(self.keystone_api.get_session())
        return self.barbican_api.nodes_exist(
            barbican.CINDER_NODE_TYPE)


class ValidateCinderAction(tables.LinkAction):
    name = "validate_cinder_node"
    verbose_name = _("Validate SSH Credentials")
    url = "horizon:admin:hpe_storage:config:validate_cinder_node"
    classes = ("ajax-modal",)

    def get_link_url(self, node):
        return reverse(self.url, args=[node['node_name']])


class EditCinderAction(tables.LinkAction):
    name = "edit_cinder_node"
    verbose_name = _("Edit Cinder Node")
    url = "horizon:admin:hpe_storage:config:edit_cinder_node"
    classes = ("ajax-modal",)


class ViewCinderSoftwareTestsAction(tables.LinkAction):
    name = "sw_cinder_tests"
    verbose_name = _("View Software Test list")
    url = "horizon:admin:hpe_storage:config:software_tests:index"
    classes = ("ajax-modal",)

    def get_link_url(self, extra_spec=None):
        return reverse(self.url, args=[barbican.CINDER_NODE_TYPE])


class TestResultsColumn(tables.Column):
    # Customized column class.
    def get_raw_data(self, node):
        if 'validation_time' in node:
            results = node['validation_time']
            if results == 'Failed':
                results = '<font color="red">FAIL</font>'
                return safestring.mark_safe(results)
            else:
                return safestring.mark_safe('<font color="green">PASS</font>')


class CinderNodeTable(tables.DataTable):
    test_name = tables.Column(
        'node_name',
        verbose_name=_('Name'),
        form_field=forms.CharField(max_length=64))
    node_ip = tables.Column(
        'node_ip',
        verbose_name=_('IP Address'),
        form_field=forms.CharField(max_length=64))
    ssh_user = tables.Column(
        'ssh_name',
        verbose_name=_('SSH Username'),
        form_field=forms.CharField(max_length=64))
    conf_file_path = tables.Column(
        'config_path',
        verbose_name=_('Config File Path'),
        form_field=forms.CharField(max_length=64))
    validated = TestResultsColumn(
        'validation_time',
        verbose_name=_('SSH Connection Test'))

    def get_object_display(self, node):
        return node['node_name']

    def get_object_id(self, node):
        return node['node_name']

    class Meta(object):
        name = "reg_cinder_nodes"
        verbose_name = _("Cinder Nodes")
        hidden_title = False
        table_actions = (RegisterCinderAction,
                         ValidateAllCinderAction,
                         ViewCinderSoftwareTestsAction,
                         DeleteCinderAction,)
        row_actions = (ValidateCinderAction,
                       EditCinderAction,
                       DeleteCinderAction)


class RegisterNovaAction(tables.LinkAction):
    name = "register_nova_node"
    verbose_name = _("Register Nova Node")
    url = "horizon:admin:hpe_storage:config:register_nova_node"
    classes = ("ajax-modal",)
    icon = "plus"


class DeleteNovaAction(tables.DeleteAction):
    name = "nova_delete"
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Nova Node",
            u"Delete Nova Nodes",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Nova Node",
            u"Deleted Nova Nodes",
            count
        )

    def delete(self, request, obj_id):
        self.keystone_api.do_setup(request)
        self.barbican_api.do_setup(self.keystone_api.get_session())
        self.barbican_api.delete_node(
            obj_id, barbican.NOVA_NODE_TYPE)


class ValidateNovaAction(tables.LinkAction):
    name = "validate_nova"
    verbose_name = _("Validate SSH Credentials")
    url = "horizon:admin:hpe_storage:config:validate_nova_node"
    classes = ("ajax-modal",)

    def get_link_url(self, node):
        return reverse(self.url, args=[node['node_name']])


class ValidateAllNovaAction(tables.LinkAction):
    name = "validate_all_nova_nodes"
    verbose_name = _("Validate SSH Credentials on All Nova Nodes")
    url = "horizon:admin:hpe_storage:config:validate_all_nova_nodes"
    classes = ("ajax-modal",)
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def allowed(self, request, node=None):
        self.keystone_api.do_setup(request)
        self.barbican_api.do_setup(self.keystone_api.get_session())
        return self.barbican_api.nodes_exist(
            barbican.NOVA_NODE_TYPE)


class ViewNovaSoftwareTestsAction(tables.LinkAction):
    name = "sw_nova_tests"
    verbose_name = _("View Software Test list")
    url = "horizon:admin:hpe_storage:config:software_tests:index"
    classes = ("ajax-modal",)

    def get_link_url(self, extra_spec=None):
        return reverse(self.url, args=[barbican.NOVA_NODE_TYPE])


class EditNovaAction(tables.LinkAction):
    name = "edit_nova_node"
    verbose_name = _("Edit Nova Node")
    url = "horizon:admin:hpe_storage:config:edit_nova_node"
    classes = ("ajax-modal",)


class NovaNodeTable(tables.DataTable):
    test_name = tables.Column(
        'node_name',
        verbose_name=_('Name'),
        form_field=forms.CharField(max_length=64))
    node_ip = tables.Column(
        'node_ip',
        verbose_name=_('IP Address'),
        form_field=forms.CharField(max_length=64))
    ssh_user = tables.Column(
        'ssh_name',
        verbose_name=_('SSH Username'),
        form_field=forms.CharField(max_length=64))
    validated = TestResultsColumn(
        'validation_time',
        verbose_name=_('SSH Connection Test'))

    def get_object_display(self, node):
        return node['node_name']

    def get_object_id(self, node):
        return node['node_name']

    class Meta(object):
        name = "reg_nova_nodes"
        verbose_name = _("Nova Nodes (Optional)")
        hidden_title = False
        table_actions = (RegisterNovaAction,
                         ValidateAllNovaAction,
                         ViewNovaSoftwareTestsAction,
                         DeleteNovaAction)
        row_actions = (ValidateNovaAction,
                       EditNovaAction,
                       DeleteNovaAction)
