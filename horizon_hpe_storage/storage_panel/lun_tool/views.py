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

from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import views
from horizon import forms
from horizon import tabs
from horizon.utils import memoized

from horizon_hpe_storage.storage_panel.lun_tool \
    import tabs as l_tabs
from horizon_hpe_storage.storage_panel.lun_tool import forms as lun_tool_forms

import horizon_hpe_storage.api.keystone_api as keystone
import horizon_hpe_storage.api.barbican_api as barbican

from openstack_dashboard.api import cinder

import logging
import time
import datetime

LOG = logging.getLogger(__name__)


class IndexView(views.HorizonTemplateView):
    template_name = 'template/index.html'


class RunLunToolView(forms.ModalFormView):
    form_class = lun_tool_forms.RunLunTool
    modal_header = _("Run Volume Path Query")
    modal_id = "run_lun_tool"
    template_name = 'lun_tool/run_lun_tool.html'
    submit_label = _("Run Query")
    submit_url = reverse_lazy(
        "horizon:admin:hpe_storage:lun_tool:run_lun_tool")
    success_url = reverse_lazy('horizon:admin:hpe_storage:index')
    page_title = _("Run Volume Path Query")


class ManageOSVarsView(forms.ModalFormView):
    form_class = lun_tool_forms.ManageOSVars
    modal_header = _("Set Default OpenStack Environment Variables")
    modal_id = "manage_os_vars_modal"
    template_name = 'lun_tool/manage_os_vars.html'
    submit_label = _("Submit")
    submit_url = reverse_lazy(
        "horizon:admin:hpe_storage:lun_tool:manage_os_vars")
    success_url = reverse_lazy('horizon:admin:hpe_storage:index')


class PathDetailView(tabs.TabView):
    tab_group_class = l_tabs.PathDetailTabs
    template_name = 'horizon/common/_detail.html'
    page_title = "Volume Path Query Results from: {{ timestamp }}"
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def get_context_data(self, **kwargs):
        context = super(PathDetailView, self).get_context_data(**kwargs)
        return context

    @memoized.memoized_method
    def get_data(self):
        timestamp = self.kwargs['timestamp']

        paths = []
        try:
            # retrieve all lun paths from lun tool results
            self.keystone_api.do_setup(self.request)
            self.barbican_api.do_setup(self.keystone_api.get_session())

            results = self.barbican_api.get_lun_tool_results()

            # grab the result that matches the timestamp
            for result in results:
                if result['timestamp'] == timestamp:
                    for node in result['node_list']:
                        for path in node['paths']:
                            path['node_name'] = node['node_name']
                            paths.append(path)
                    break

        except Exception as ex:
            redirect = self.get_redirect_url()
            exceptions.handle(self.request,
                              _('Unable to retrieve volume paths.'),
                              redirect=redirect)

        return paths

    def get_redirect_url(self):
        return reverse('horizon:admin:hpe_storage:index')

    def get_tabs(self, request, *args, **kwargs):
        volume_paths = self.get_data()
        return self.tab_group_class(request,
                                    volume_paths=volume_paths,
                                    **kwargs)


class ShowDiffView(forms.ModalFormView):
    form_class = lun_tool_forms.ShowDiff
    modal_header = _("Compare Query Results")
    modal_id = "show_diff_modal"
    template_name = 'lun_tool/show_diff.html'
    submit_label = _("Submit")
    submit_url = "horizon:admin:hpe_storage:lun_tool:show_diff"
    success_url = "horizon:admin:hpe_storage:lun_tool:diff_details"
    page_title = _("Edit Nova Node")

    def get_context_data(self, **kwargs):
        context = super(ShowDiffView, self).get_context_data(**kwargs)
        args = (self.kwargs['timestamp'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_success_url(self):
        str_timestamp_1 = self.request.REQUEST['other_results']
        str_timestamp_2 = self.kwargs['timestamp']
        timestamp_1 = time.mktime(
            datetime.datetime.strptime(str_timestamp_1,
                                       '%Y-%m-%d %H:%M:%S').timetuple())
        timestamp_2 = time.mktime(
            datetime.datetime.strptime(str_timestamp_2,
                                       '%Y-%m-%d %H:%M:%S').timetuple())
        # ensure that oldest query result is the base for comparison
        if timestamp_1 <= timestamp_2:
            return reverse(self.success_url,
                           args=(str_timestamp_1 + "::" + str_timestamp_2,))
        else:
            return reverse(self.success_url,
                           args=(str_timestamp_2 + "::" + str_timestamp_1,))

    def get_link_url(self, datum):
        timestamp = datum['timestamp']
        link_url = "lun_tool/" + timestamp + "/path_detail"
        return link_url

    def get_initial(self):
        timestamp = self.kwargs['timestamp']
        return {'timestamp': timestamp}


class DiffDetailView(tabs.TabView):
    tab_group_class = l_tabs.DiffDetailTabs
    template_name = 'horizon/common/_detail.html'
    page_title = "Compare Results from: [{{ base_timestamp }}] to: " \
                 "[{{ compare_timestamp }}]"
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def get_context_data(self, **kwargs):
        context = super(DiffDetailView, self).get_context_data(**kwargs)
        timestamps = context['timestamp'].split("::")
        context['base_timestamp'] = timestamps[0]
        context['compare_timestamp'] = timestamps[1]
        return context

    @memoized.memoized_method
    def get_data(self):
        timestamps = self.kwargs['timestamp'].split("::")
        base_timestamp = timestamps[0]
        compare_timestamp = timestamps[1]
        diff_data = {}

        try:
            # retrieve all lun paths from lun tool results
            self.keystone_api.do_setup(self.request)
            self.barbican_api.do_setup(self.keystone_api.get_session())

            results = self.barbican_api.get_lun_tool_results()

            # grab the query results that match the base and compare timestamps
            found_results = 0
            for result in results:
                if result['timestamp'] == base_timestamp:
                    base_result = result
                    found_results += 1
                elif result['timestamp'] == compare_timestamp:
                    compare_result = result
                    found_results += 1
                if found_results > 1:
                    break

            # compare results
            # fist check if any nova nodes have been added or removed
            removed_nodes = self.find_new_nodes(compare_result['node_list'],
                                                base_result['node_list'])

            added_nodes = self.find_new_nodes(base_result['node_list'],
                                              compare_result['node_list'])

            # now check for added/removed paths within each nova node
            modified_paths = []
            for base_node in base_result['node_list']:
                found_node = [d for d in compare_result['node_list']
                              if d['node_name'] == base_node['node_name']]

                if found_node:
                    added_paths = self.find_new_paths(base_node['paths'],
                                                      found_node[0]['paths'])
                    removed_paths = self.find_new_paths(found_node[0]['paths'],
                                                        base_node['paths'])
                    if removed_paths:
                        for removed_path in removed_paths:
                            entry = {}
                            entry['node_name'] = base_node['node_name']
                            entry['old_path'] = removed_path
                            entry['new_path'] = None
                            modified_paths.append(entry)
                    if added_paths:
                        for added_path in added_paths:
                            entry = {}
                            entry['node_name'] = base_node['node_name']
                            entry['old_path'] = None
                            entry['new_path'] = added_path
                            modified_paths.append(entry)

            # check if any paths have been modified
            for base_node in base_result['node_list']:
                found_node = [d for d in compare_result['node_list']
                              if d['node_name'] == base_node['node_name']]

                if found_node:
                    changed_paths = \
                        self.find_changed_paths(base_node['node_name'],
                                                base_node['paths'],
                                                found_node[0]['paths'])

                    if changed_paths:
                        for changed_path in changed_paths:
                            modified_paths.append(changed_path)

            diff_data['removed_nodes'] = removed_nodes
            diff_data['added_nodes'] = added_nodes
            diff_data['modified_paths'] = modified_paths

        except Exception as ex:
            redirect = self.get_redirect_url()
            exceptions.handle(self.request,
                              _('Unable to retrieve volume paths.'),
                              redirect=redirect)

        return diff_data

    def find_new_nodes(self, old_node_list, new_node_list):
        new_nodes = []
        for node in new_node_list:
            found_node = [d for d in old_node_list
                          if d['node_name'] == node['node_name']]

            if not found_node:
                new_nodes.append(node)

        return new_nodes

    def find_new_paths(self, old_path_list, new_path_list):
        new_paths = []
        for path in new_path_list:
            found_path = [d for d in old_path_list
                          if d['path'] == path['path']]

            if not found_path:
                new_paths.append(path)

        return new_paths

    def find_changed_paths(self, node_name, old_path_list, new_path_list):
        changed_paths = []
        for path in new_path_list:
            found_path = [d for d in old_path_list
                          if d['path'] == path['path']]

            if found_path:
                found_path_entry = found_path[0]
                if found_path_entry['path'] != path['path'] or \
                    found_path_entry['vol_name'] != path['vol_name'] or \
                        found_path_entry['vol_id'] != path['vol_id']:
                    changed_path = {}
                    changed_path['node_name'] = node_name
                    changed_path['new_path'] = path
                    changed_path['old_path'] = found_path_entry
                    changed_paths.append(changed_path)

        return changed_paths

    def get_redirect_url(self):
        return reverse('horizon:admin:hpe_storage:index')

    def get_tabs(self, request, *args, **kwargs):
        diff_data = self.get_data()
        return self.tab_group_class(request, diff_data=diff_data, **kwargs)
