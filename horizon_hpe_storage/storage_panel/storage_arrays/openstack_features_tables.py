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


class OpenstackFeaturesTable(tables.DataTable):
    feature = tables.Column(
        'name',
        verbose_name=_('OpenStack Storage Feature'),
        form_field=forms.CharField(max_length=64))
    requirements = tables.Column(
        'requirements',
        verbose_name=_('Required Array Licenses'),
        form_field=forms.CharField(max_length=64))
    enabled = tables.Column(
        'enabled',
        verbose_name=_('Enabled'),
        form_field=forms.CharField(max_length=64))

    class Meta(object):
        name = "features"
        verbose_name = _("OpenStack Storage Features")
        # hidden_title = False

    def get_object_id(self, datum):
        return datum.get('name', id(datum))
