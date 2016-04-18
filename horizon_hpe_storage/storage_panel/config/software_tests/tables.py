#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import tables
from horizon import forms

import horizon_hpe_storage.api.keystone_api as keystone
import horizon_hpe_storage.api.barbican_api as barbican


class SoftwareTestDelete(tables.DeleteAction):
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Software Package",
            u"Delete Software Packages",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Software Package",
            u"Deleted Software Packages",
            count
        )

    def delete(self, request, obj_id):
        self.keystone_api.do_setup(request)
        self.barbican_api.do_setup(self.keystone_api.get_session())
        node_type = self.table.kwargs['node_type']
        self.barbican_api.delete_software_test(node_type, obj_id)


class SoftwareTestCreate(tables.LinkAction):
    name = "create"
    verbose_name = _("Add Software Package")
    url = "horizon:admin:hpe_storage:config:software_tests:create"
    classes = ("ajax-modal",)
    icon = "plus"

    def get_link_url(self, package=None):
        return reverse(self.url, args=[self.table.kwargs['node_type']])


class SoftwareTestEdit(tables.LinkAction):
    name = "edit"
    verbose_name = _("Edit")
    url = "horizon:admin:hpe_storage:config:software_tests:edit"
    classes = ("btn-edit", "ajax-modal")

    def get_link_url(self, package):
        return reverse(self.url, args=[self.table.kwargs['node_type'],
                                       package['package']])


class SoftwareTestsTable(tables.DataTable):
    package = tables.Column('package',
                            verbose_name=_('Softare Package'))
    min_version = tables.Column('min_version',
                                verbose_name=_('Minimum Version'))
    description = tables.Column("description",
                                verbose_name=_("Description"),
                                truncate=40)

    class Meta(object):
        name = "tests"
        table_actions = (SoftwareTestCreate, SoftwareTestDelete)
        row_actions = (SoftwareTestEdit, SoftwareTestDelete)

    def get_object_id(self, datum):
        return datum['package']

    def get_object_display(self, datum):
        return datum['package']
