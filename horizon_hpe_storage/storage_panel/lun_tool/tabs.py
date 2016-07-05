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
from django.utils import safestring

from horizon import tabs

from horizon_hpe_storage.storage_panel.lun_tool \
    import volume_path_tables as v_tables
from horizon_hpe_storage.storage_panel.lun_tool \
    import diff_tables as d_tables


class PathDetailTab(tabs.TableTab):
    name = _("Volume Paths")
    slug = "paths"
    table_classes = (v_tables.VolumePathsTable,)
    template_name = "lun_tool/_detail_paths.html"

    def get_paths_data(self):
        volume_paths = self.tab_group.kwargs['volume_paths']
        return volume_paths


class PathDetailTabs(tabs.TabGroup):
    slug = "path_details"
    tabs = (PathDetailTab,)


class DiffDetailTab(tabs.TableTab):
    name = _("Diffs")
    slug = "diffs"
    table_classes = (d_tables.DiffTable,)
    template_name = "lun_tool/detail_diffs.html"

    def get_diffs_data(self):
        diffs = self.tab_group.kwargs['diffs']
        return diffs

    def get_diff_paths_data(self):
        path_list = []
        added_list = []
        removed_list = []
        changed_list = []
        id = 0

        diff = self.tab_group.kwargs['diff_data']
        if diff and 'added_nodes' in diff:
            added_nodes = diff['added_nodes']
            for node in added_nodes:
                for path in node['paths']:
                    path_entry = {}
                    path_entry['diff'] = "Node Added"
                    path_entry['node_name'] = node['node_name']
                    path_entry['old_path'] = "-"
                    path_entry['new_path'] = \
                        self.build_field(node['node_name'],
                                         path['path'],
                                         path['vol_name'],
                                         path['vol_id'])
                    path_entry['id'] = id
                    id += 1
                    added_list.append(path_entry)

        if diff and 'removed_nodes' in diff:
            removed_nodes = diff['removed_nodes']
            for node in removed_nodes:
                for path in node['paths']:
                    path_entry = {}
                    path_entry['diff'] = "Node Removed"
                    path_entry['node_name'] = node['node_name']
                    path_entry['old_path'] = \
                        self.build_field(node['node_name'],
                                         path['path'],
                                         path['vol_name'],
                                         path['vol_id'])
                    path_entry['new_path'] = "-"
                    path_entry['id'] = id
                    id += 1
                    removed_list.append(path_entry)

        if diff and 'modified_paths' in diff:
            modified_paths = diff['modified_paths']
            for modified_path in modified_paths:
                path_entry = {}
                path_entry['diff'] = "Path Modified"
                old_path = modified_path['old_path']
                if old_path:
                    path_entry['old_path'] = \
                        self.build_field(modified_path['node_name'],
                                         old_path['path'],
                                         old_path['vol_name'],
                                         old_path['vol_id'])
                else:
                    path_entry['diff'] = "Path Added"
                    path_entry['old_path'] = "-"

                new_path = modified_path['new_path']
                if new_path:
                    path_entry['new_path'] = \
                        self.build_field(modified_path['node_name'],
                                         new_path['path'],
                                         new_path['vol_name'],
                                         new_path['vol_id'])
                else:
                    path_entry['diff'] = "Path Removed"
                    path_entry['new_path'] = "-"

                path_entry['node_name'] = modified_path['node_name']
                path_entry['id'] = id
                id += 1
                if path_entry['diff'] == "Path Added":
                    added_list.append(path_entry)
                elif path_entry['diff'] == "Path Removed":
                    removed_list.append(path_entry)
                else:
                    changed_list.append(path_entry)

        path_list.extend(sorted(added_list, key=lambda k: k['node_name']))
        path_list.extend(sorted(removed_list, key=lambda k: k['node_name']))
        path_list.extend(sorted(changed_list, key=lambda k: k['node_name']))
        return path_list

    def build_field(self, node_name, path, vol_name, vol_id):
        path_str = \
            "<b>Node:  </b>" + \
            node_name + "  " + \
            "<br>" + \
            "<b>Vol Path:  </b>" + \
            path + "  " + \
            "<br>" + \
            "<b>Vol Name:  </b>" + \
            vol_name + "  " + \
            "<br>" + \
            "<b>Vol ID:  </b>" + \
            vol_id + "  "
        return safestring.mark_safe(path_str)


class DiffDetailTabs(tabs.TabGroup):
    slug = "diff_details"
    tabs = (DiffDetailTab,)
