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


class TestDescriptionTable(tables.DataTable):
    test = tables.Column(
        'test',
        verbose_name=_('Test'),
        form_field=forms.CharField(max_length=64))
    entries = tables.Column(
        'entries_used',
        verbose_name=_('Utilized Driver Configuration Entries'),
        form_field=forms.CharField(max_length=255))
    description = tables.Column(
        'description',
        verbose_name=_('Description'),
        form_field=forms.CharField(max_length=255))

    class Meta(object):
        name = "test_descriptions"
        verbose_name = _("Cinder Backend Test Descriptions")
        hidden_title = False

    def get_object_id(self, datum):
        return datum.get('test', id(datum))


class BackendTestTable(tables.DataTable):
    backend = tables.Column(
        'backend_name',
        verbose_name=_('Driver Configuration'),
        form_field=forms.CharField(max_length=64))
    credentials = tables.Column(
        'credentials',
        verbose_name=_('Credentials'),
        form_field=forms.CharField(max_length=64))
    wsapi = tables.Column(
        'wsapi',
        verbose_name=_('WS API'),
        form_field=forms.CharField(max_length=64))
    cpgs = tables.Column(
        'cpgs',
        verbose_name=_('CPGs'),
        form_field=forms.CharField(max_length=64))
    iscsi = tables.Column(
        'iscsi',
        verbose_name=_('iSCSI IP(s)'),
        form_field=forms.CharField(max_length=64))
    driver = tables.Column(
        'driver',
        verbose_name=_('Volume Driver'),
        form_field=forms.CharField(max_length=64))

    class Meta(object):
        name = "backend_test_results"
        verbose_name = _("Cinder Backend Test Results")
        hidden_title = False

    def get_object_id(self, datum):
        return datum.get('backend_name', id(datum))


class SoftwareTestTable(tables.DataTable):
    package = tables.Column(
        'package',
        verbose_name=_('Software Package'),
        form_field=forms.CharField(max_length=64))
    description = tables.Column(
        'description',
        verbose_name=_('Description'),
        form_field=forms.CharField(max_length=64))
    min_version = tables.Column(
        'min_version',
        verbose_name=_('Min Version Required'),
        form_field=forms.CharField(max_length=64))
    curr_version = tables.Column(
        'curr_version',
        verbose_name=_('Installed Version'),
        form_field=forms.CharField(max_length=64))
    test_result = tables.Column(
        'test_result',
        verbose_name=_('Test Result'),
        form_field=forms.CharField(max_length=64))

    class Meta(object):
        name = "software_test_results"
        verbose_name = _("Software Test Results")
        hidden_title = False

    def get_object_id(self, datum):
        return datum.get('license', id(datum))