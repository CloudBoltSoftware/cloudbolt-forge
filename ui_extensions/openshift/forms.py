import ast
from django import forms

from utilities.forms import ConnectionInfoForm
from utilities.models import ConnectionInfo

from xui.openshift.openshiftmanager import OpenshiftManager


class OpenShiftConectionForm(ConnectionInfoForm):
    protocol = forms.ChoiceField(
        choices=[('https', 'HTTPS'), ('http', 'HTTP')], label='Protocol')

    def __init__(self, *args, **kwargs):
        super(OpenShiftConectionForm, self).__init__(*args, **kwargs)

        self.fields["name"].widget = forms.HiddenInput()
        self.fields["name"].initial = "Openshift Connection Info"
        self.fields["protocol"].initial = "HTTPS"
        self.fields["port"].initial = 443
        self.fields["headers"].initial = {"token": ""}

        # Remove connection info fields we do not need in openshift credentials
        del self.fields['ssh_key']
        del self.fields['username']
        del self.fields['password']
        del self.fields['use_auth_headers']

        # mark all fields as required
        for field in list(self.fields.values()):
            field.required = True

    def clean(self):
        ip = self.cleaned_data.get('ip')
        protocol = self.cleaned_data.get('protocol')
        port = self.cleaned_data.get('port')
        headers = ast.literal_eval(self.cleaned_data.get('headers'))
        token = headers.get('token')

        openshiftmanager = OpenshiftManager(ip, token, port, protocol)
        response = openshiftmanager.verify_rest_credentials()

        if response == False:
            raise forms.ValidationError(
                "Unable to connect to openshift server using the parameters provided. Please enter the credentials "
                "correctly "
            )

        return self.cleaned_data

    def save(self, *args, **kwargs):
        credentials = super(OpenShiftConectionForm,
                            self).save(*args, **kwargs)
        return credentials
