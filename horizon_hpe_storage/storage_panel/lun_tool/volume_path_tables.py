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

from horizon import forms
from horizon import tables


class PathsFilterAction(tables.FilterAction):

    def filter(self, table, paths, filter_string):
        """Naive case-insensitive search."""
        q = filter_string.lower()
        return [path for path in paths
                if q in path.node_name.lower()]


class VolumePathsTable(tables.DataTable):
    node = tables.Column(
        'node_name',
        verbose_name=_('Nova Node'),
        form_field=forms.CharField(max_length=64))
    path = tables.Column(
        'path',
        verbose_name=_('Volume Path'),
        form_field=forms.CharField(max_length=64))
    vol_name = tables.Column(
        'vol_name',
        verbose_name=_('Attached Volume Name'),
        form_field=forms.CharField(max_length=64))
    vol_id = tables.Column(
        'vol_id',
        verbose_name=_('Attached Volume ID'),
        form_field=forms.CharField(max_length=64))

    class Meta(object):
        name = "paths"
        verbose_name = _("Volume Paths")
        # hidden_title = False
        table_actions = (PathsFilterAction,)

    def get_object_id(self, datum):
        return datum.get('path', id(datum))
