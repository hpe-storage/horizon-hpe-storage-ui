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

from horizon import forms
from horizon import tables
from difflib import Differ


class AddedNodesTable(tables.DataTable):
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
        name = "added_nodes"
        verbose_name = _("Added Nodes")
        hidden_title = False

    def get_object_id(self, datum):
        return datum.get('node', id(datum))


class RemovedNodesTable(tables.DataTable):
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
        name = "removed_nodes"
        verbose_name = _("Removed Nodes")
        hidden_title = False

    def get_object_id(self, datum):
        return datum.get('node', id(datum))


class ModifiedPathsTable(tables.DataTable):
    old_path = tables.Column(
        'old_path',
        verbose_name=_('Original Path'),
        form_field=forms.CharField(max_length=64))
    modified_path = tables.Column(
        'new_path',
        verbose_name=_('Modified Path'),
        form_field=forms.CharField(max_length=64))

    class Meta(object):
        name = "modified_paths"
        verbose_name = _("Modified Paths")
        hidden_title = False

    def get_object_id(self, datum):
        return datum.get('old_path', id(datum))


class OldPathColumn(tables.Column):
    # Customized column class.
    def get_raw_data(self, results):
        # results = '<font color="red">FAIL</font>'

        old_path = results['old_path']
        new_path = results['new_path']

        if old_path == '-' or new_path == '-':
            return old_path

        if new_path == old_path:
            return old_path

        l1 = new_path.split(' ')
        l2 = old_path.split(' ')
        dif = list(Differ().compare(l1, l2))
        tt = " ".join(['<font color="red">'+i[2:]+'</font>'
                       if i[:1] == '+' else i[2:] for i in dif
                       if not i[:1] in '-?'])
        return safestring.mark_safe(tt)


class NewPathColumn(tables.Column):
    # Customized column class.
    def get_raw_data(self, results):
        # results = '<font color="red">FAIL</font>'

        old_path = results['old_path']
        new_path = results['new_path']

        if old_path == '-' or new_path == '-':
            return new_path

        if new_path == old_path:
            return new_path

        l1 = old_path.split('  ')
        l2 = new_path.split('  ')
        dif = list(Differ().compare(l1, l2))
        tt = " ".join(['<font color="red">'+i[2:]+'</font>'
                       if i[:1] == '+' else i[2:] for i in dif
                       if not i[:1] in '-?'])
        return safestring.mark_safe(tt)


class DiffTable(tables.DataTable):
    diff = tables.Column(
        'diff',
        verbose_name=_('Change'),
        form_field=forms.CharField(max_length=64))
    old_path = OldPathColumn(
        'old_path',
        verbose_name=_('Old Path'))
    new_path = NewPathColumn(
        'new_path',
        verbose_name=_('New Path'))

    class Meta(object):
        name = "diff_paths"
        verbose_name = _("Volume Path Changes")
        hidden_title = False

    def get_object_id(self, datum):
        return datum.get('id', id(datum))
