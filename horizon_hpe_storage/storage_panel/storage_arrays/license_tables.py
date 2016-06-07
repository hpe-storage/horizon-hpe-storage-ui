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


class LicenseTable(tables.DataTable):
    license = tables.Column(
        'license',
        verbose_name=_('License'),
        form_field=forms.CharField(max_length=64))
    expire_date = tables.Column(
        'exp_date',
        verbose_name=_('Expiration Date'),
        form_field=forms.CharField(max_length=64))

    class Meta(object):
        name = "licenses"
        verbose_name = _("Storage System Licenses")
        # hidden_title = False

    def get_object_id(self, datum):
        return datum.get('license', id(datum))
