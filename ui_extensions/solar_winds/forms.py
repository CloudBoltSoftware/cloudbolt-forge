from django import forms
from django.utils.translation import ugettext as _, ugettext_lazy as _lazy
from utilities.forms import ConnectionInfoForm
from utilities.models import ConnectionInfo
from xui.solar_winds.solar_winds_helper import SolarWindsManager
from xui.solar_winds import views


class SolarWindsConectionForm(ConnectionInfoForm):

    protocol = forms.ChoiceField(
        choices=[('http', 'HTTP'), ('https', 'HTTPS')], label='Protocol')

    def __init__(self, *args, **kwargs):
        super(SolarWindsConectionForm, self).__init__(*args, **kwargs)

        self.fields["name"].widget = forms.HiddenInput()
        self.fields["name"].initial = "SolarWinds Connection Info Rest"
        self.fields["protocol"].initial = "HTTPS"

        # Remove connection info fields we do not need in solarwinds credentials
        del self.fields['ssh_key']
        del self.fields['use_auth_headers']
        del self.fields['headers']

        # mark all fields as required
        for field in list(self.fields.values()):
            field.required = True

    def clean(self):
        solarwindsmanager = SolarWindsManager()
        response = solarwindsmanager.verify_rest_credentials(
            connection_info=ConnectionInfo(
                protocol=self.cleaned_data.get('protocol'),
                ip=self.cleaned_data.get('ip'),
                port=self.cleaned_data.get('port'),
                username=self.cleaned_data.get('username'),
                password=self.cleaned_data.get('password'),
            )
        )

        if response == False:
            raise forms.ValidationError(
                "Unable to connect to solarwinds server using the parameters provided. Please enter the credentials correctly"
            )

        return self.cleaned_data

    def save(self, *args, **kwargs):
        credentials = super(SolarWindsConectionForm,
                            self).save(*args, **kwargs)
        return credentials


class SolarWindsServerConectionForm(ConnectionInfoForm):
    def __init__(self, *args, **kwargs):
        super(SolarWindsServerConectionForm, self).__init__(*args, **kwargs)

        self.fields["name"].widget = forms.HiddenInput()
        self.fields["name"].initial = "SolarWinds Connection Info"

        # Remove connection info fields we do not need in solarwinds credentials
        del self.fields['ssh_key']
        del self.fields['use_auth_headers']
        del self.fields['headers']
        del self.fields['port']
        del self.fields['protocol']

        # mark all fields as required
        for field in list(self.fields.values()):
            field.required = True

    def clean(self):
        solarwindsmanager = SolarWindsManager()
        response = solarwindsmanager.verify_server_connection(
            server_connection_info=ConnectionInfo(
                ip=self.cleaned_data.get('ip'),
                username=self.cleaned_data.get('username'),
                password=self.cleaned_data.get('password'),
            )
        )
        if not response[0]:
            raise forms.ValidationError(response[1])
        return self.cleaned_data

    def save(self, *args, **kwargs):
        credentials = super(SolarWindsServerConectionForm,
                            self).save(*args, **kwargs)
        return credentials
