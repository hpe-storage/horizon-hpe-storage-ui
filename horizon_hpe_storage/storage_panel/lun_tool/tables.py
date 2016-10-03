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
from django.core.urlresolvers import reverse
from django.utils.translation import ungettext_lazy

from horizon import forms
from horizon import tables

import horizon_hpe_storage.api.keystone_api as keystone
import horizon_hpe_storage.api.barbican_api as barbican

import datetime


class RunLunToolAction(tables.LinkAction):
    name = "run_lun_tool"
    verbose_name = _("Run Volume Path Query")
    url = "horizon:admin:hpe_storage:lun_tool:run_lun_tool"
    classes = ("ajax-modal",)
    icon = "plus"


class ManageOSVariables(tables.LinkAction):
    name = "manage_os_vars"
    verbose_name = _("Set Default OpenStack Variables")
    url = "horizon:admin:hpe_storage:lun_tool:manage_os_vars"
    classes = ("ajax-modal",)


class DeleteResultAction(tables.DeleteAction):
    name = "delete_result"
    policy_rules = (("volume", "volume:deep_link"),)
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Query Result",
            u"Delete Query Results",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Query Result",
            u"Deleted Query Results",
            count
        )

    def delete(self, request, timestamp):
        self.keystone_api.do_setup(request)
        self.barbican_api.do_setup(self.keystone_api.get_session())

        return self.barbican_api.delete_lun_tool_result(timestamp)


class ShowDiffAction(tables.LinkAction):
    name = "diff_results"
    verbose_name = _("Show Difference Between Queries")
    url = "horizon:admin:hpe_storage:lun_tool:show_diff"
    classes = ("ajax-modal",)

    def allowed(self, request, nodes=None):
        return True


class DisplayPathsAction(tables.LinkAction):
    name = "paths"
    verbose_name = _("View Volume Paths")
    classes = ("btn-log",)

    def get_link_url(self, datum):
        timestamp = datum['timestamp']
        link_url = "lun_tool/" + timestamp + "/path_detail"
        return link_url


class TimeStampColumn(tables.Column):
    def get_raw_data(self, data):
        str = data['timestamp'].split('-')
        timestr = str[0] + '-' + str[1] + '-' + str[2]
        timestr += '  '
        idx = 3
        while idx < len(str):
            timestr += str[idx]
            idx += 1
            if idx < len(str):
                timestr += ':'

        return timestr


class NumNodesColumn(tables.Column):
    # Customized column class.
    def get_raw_data(self, results):
        node_list = results['node_list']
        return len(node_list)


class NumPathsColumn(tables.Column):
    # Customized column class.
    def get_raw_data(self, results):
        cnt = 0
        node_list = results['node_list']
        for node in node_list:
            cnt += len(node['paths'])
        return cnt


class NumAttachedColumn(tables.Column):
    # Customized column class.
    def get_raw_data(self, results):
        cnt = 0
        node_list = results['node_list']
        for node in node_list:
            paths = node['paths']
            for path in paths:
                if path['vol_id']:
                    cnt += 1
        return cnt


class LunToolTable(tables.DataTable):
    timestamp = tables.Column(
        'timestamp',
        verbose_name=_('Run Time'),
        form_field=forms.CharField(max_length=64))
    num_nodes = NumNodesColumn(
        'num_nodes',
        verbose_name=_('Number of Nova Nodes Queried'))
    num_paths = NumPathsColumn(
        'num_paths',
        verbose_name=_('Total Number of Discovered Volume Paths'))
    num_attached = NumAttachedColumn(
        'num_attached',
        verbose_name=_('Total Number of Attached Volumes'))

    def get_object_id(self, result):
        return result['timestamp']

    def get_object_display(self, result):
        return result['timestamp']

    class Meta(object):
        name = "lun_volume_paths"
        verbose_name = _("Volume Path Query Results")
        hidden_title = False
        table_actions = (RunLunToolAction, ManageOSVariables,
                         DeleteResultAction)
        row_actions = (DisplayPathsAction, ShowDiffAction, DeleteResultAction)
