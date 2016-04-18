# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

import horizon_hpe_storage.api.keystone_api as keystone
import horizon_hpe_storage.api.barbican_api as barbican

from horizon import exceptions
from horizon import forms
from horizon import messages


class AddSoftwareTest(forms.SelfHandlingForm):
    sw_package = forms.CharField(max_length=255, label=_("Software Package"))
    min_version = forms.CharField(max_length=255, label=_("Minimum Version"))
    description = forms.CharField(max_length=255,
                                  required=False,
                                  label=_("Description"))
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def handle(self, request, data):
        node_type = self.initial['node_type']
        try:
            self.keystone_api.do_setup(self.request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            self.barbican_api.add_software_test(node_type, data['sw_package'],
                                                data['min_version'],
                                                data['description'])
            msg = _('Added softare package "%s".') % data['sw_package']
            messages.success(request, msg)
            return True
        except Exception:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _("Unable to add softare package."),
                              redirect=redirect)


class EditSoftwareTest(forms.SelfHandlingForm):
    min_version = forms.CharField(max_length=255, label=_("Minimum Version"))
    description = forms.CharField(max_length=255,
                                  required=False,
                                  label=_("Description"))
    keystone_api = keystone.KeystoneAPI()
    barbican_api = barbican.BarbicanAPI()

    def handle(self, request, data):
        sw_package = self.initial['sw_package']
        node_type = self.initial['node_type']
        try:
            self.keystone_api.do_setup(self.request)
            self.barbican_api.do_setup(self.keystone_api.get_session())
            self.barbican_api.update_software_test(node_type, sw_package,
                                                   data['min_version'],
                                                   data['description'])
            msg = _('Saved softare package "%s".') % sw_package
            messages.success(request, msg)
            return True
        except Exception:
            redirect = reverse("horizon:admin:hpe_storage:index")
            exceptions.handle(request,
                              _("Unable to save softare package."),
                              redirect=redirect)
