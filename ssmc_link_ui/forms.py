# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2012 Nebula, Inc.
#
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
from django.forms import ValidationError  # noqa
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages
from django.http import HttpResponseRedirect
from django import forms as dj_forms

import logging

LOG = logging.getLogger(__name__)
import webbrowser

import api.keystone_api as keystone
import api.barbican_api as barbican
import api.cinder_api as cinder



class CreateEndpoint(forms.SelfHandlingForm):
    backend = forms.ChoiceField(label=_("Available Cinder Backends"))
    endpoint = forms.CharField(max_length=255,
                               label=_("SSMC Endpoint"))
    uname = forms.CharField(max_length=255,
                            label=_("SSMC Username"))
    pwd  = forms.CharField(max_length=255,
                           widget=dj_forms.PasswordInput,
                           label=_("SSMC Password"))

    def __init__(self, request, *args, **kwargs):
        super(forms.SelfHandlingForm, self).__init__(request, *args, **kwargs)

        # get list of backend names from cinder
        keystone_api = keystone.KeystoneAPI()
        keystone_api.do_setup(None)
        keystone_api.client_login()
        endpoints = keystone_api.get_ssmc_endpoints()

        cinder_api = cinder.CinderAPI()
        cinder_api.do_setup(None)
        backends = cinder_api.get_pools(keystone_api.get_session_key(),
                                        keystone_api.get_tenant_id())
        choices = []
        for backend in backends:
            # only show backends that haven't been assigned an endpoint
            matchFound = False
            for endpoint in endpoints:
                if endpoint['backend'] == backend:
                    matchFound = True
                    break
            if not matchFound:
                choice = forms.ChoiceField = (backend, backend)
                choices.append(choice)

        self.fields['backend'].choices = choices

    def handle(self, request, data):
        try:
            # create new keypoint service and endpoint
            keystone_api = keystone.KeystoneAPI()
            keystone_api.do_setup(None)
            keystone_api.client_login()
            backend_name = 'ssmc-' + data['backend']
            keystone_api.add_ssmc_endpoint(backend_name,
                                          data['endpoint'])

            # store credentials for endpoint using barbican
            barbican_api = barbican.BarbicanAPI()
            barbican_api.do_setup(None)
            barbican_api.add_credentials(keystone_api.get_session_key(),
                                         backend_name,
                                         data['uname'],
                                         data['pwd'])

            messages.success(request, _('Successfully created endpoint '
                                        'for backend: %s') % data['backend'])
            return True
        except Exception as ex:
            redirect = reverse("horizon:admin:volumes:index")
            exceptions.handle(request,
                              _('Unable to create encrypted volume type.'),
                              redirect=redirect)


class EditEndpoint(forms.SelfHandlingForm):
    backend = forms.CharField(label=_("Cinder Backend"),
                           required=False,
                           widget=forms.TextInput(
                           attrs={'readonly': 'readonly'}))
    endpoint = forms.CharField(max_length=255,
                               label=_("SSMC Endpoint"))
    uname = forms.CharField(max_length=255,
                            label=_("SSMC Username"))
    pwd  = forms.CharField(max_length=255,
                           widget=dj_forms.PasswordInput,
                           label=_("SSMC Password"))

    def __init__(self, request, *args, **kwargs):
        super(EditEndpoint, self).__init__(request, *args, **kwargs)
        service_id = self.initial['service_id']

        backend_field = self.fields['backend']
        endpoint_field = self.fields['endpoint']
        uname_field = self.fields['uname']
        pwd_field = self.fields['pwd']

        keystone_api = keystone.KeystoneAPI()
        keystone_api.do_setup(None)
        keystone_api.client_login()

        # initialize endpoint fields
        endpoint, name = keystone_api.get_ssmc_endpoint_for_service_id(service_id)
        backend_name = name[5:]    # remove 'ssmc-' prefix
        backend_field.initial = backend_name
        endpoint_field.initial = endpoint['url']

        # initialize credentials fields
        barbican_api = barbican.BarbicanAPI()
        barbican_api.do_setup(None)
        uname, pwd = barbican_api.get_credentials(keystone_api.get_session_key(),
                                                  backend_name)
        uname_field.initial = uname
        pwd_field.initial = pwd
        pwd_field.widget.render_value = True  # this makes it show up initially

        # save off current values

    def clean(self):
        form_data = self.cleaned_data

        # ensure that data has changed
        endpoint_field = self.fields['endpoint']
        uname_field = self.fields['uname']
        pwd_field = self.fields['pwd']

        if form_data['endpoint'] == endpoint_field.initial:
            if form_data['uname'] == uname_field.initial:
                if form_data['pwd'] == pwd_field.initial:
                    raise forms.ValidationError(
                        _('No fields have been modified.'))
        return form_data

    def handle(self, request, data):
        try:
            endpoint_field = self.fields['endpoint']
            uname_field = self.fields['uname']
            pwd_field = self.fields['pwd']

            keystone_api = keystone.KeystoneAPI()
            keystone_api.do_setup(None)
            keystone_api.client_login()
            backend_name = 'ssmc-' + data['backend']

            # only update endpoint if it has changed
            new_endpoint = data['endpoint']
            if new_endpoint != endpoint_field.initial:
                service_id = self.initial['service_id']
                keystone_api.update_ssmc_endpoint_url(service_id, new_endpoint)

            # only update credentials if they have changed
            new_uname = data['uname']
            new_pwd = data['pwd']
            host = data['backend']
            if new_uname != uname_field.initial:
                barbican_api = barbican.BarbicanAPI()
                barbican_api.do_setup(None)
                barbican_api.update_user_name(keystone_api.get_session_key(),
                                              host,
                                              new_uname)

            if new_pwd != pwd_field.initial:
                barbican_api = barbican.BarbicanAPI()
                barbican_api.do_setup(None)
                barbican_api.update_password(keystone_api.get_session_key(),
                                              host,
                                              new_pwd)

            messages.success(request, _('Successfully update endpoint '
                                        'for backend: %s') % data['backend'])
            return True
        except Exception:
            redirect = reverse("horizon:admin:volumes:index")
            exceptions.handle(request,
                              _('Unable to update endpoint.'),
                              redirect=redirect)


class LinkToSSMC(forms.SelfHandlingForm):
    name = forms.CharField(max_length=255, label=_("Volume"),
                           widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    def handle(self, request, data):
        try:
            link_url = self.initial['link_url']
            LOG.info(("## LAUNCH URL: %s") % link_url)
            # webbrowser.open(link_url)

            from django.http import HttpResponse
            response = HttpResponse("", status=302)
            response['Location'] = link_url
            HttpResponseRedirect(link_url)
            # return True
        except Exception:
            exceptions.handle(request,
                              _('Unable to link to SSMC.'))

