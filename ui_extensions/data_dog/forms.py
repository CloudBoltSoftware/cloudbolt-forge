from django import forms
from utilities.forms import ConnectionInfoForm
from utilities.models import ConnectionInfo

from xui.data_dog.data_dog_helper import DataDog


class DataDogConnectionForm(ConnectionInfoForm):
    protocol = forms.ChoiceField(
        choices=[('http', 'HTTP'), ('https', 'HTTPS')], label='Protocol')

    def __init__(self, *args, **kwargs):
        super(DataDogConnectionForm, self).__init__(*args, **kwargs)

        self.fields["name"].widget = forms.HiddenInput()
        self.fields["name"].initial = "Datadog Connection Credentials"
        self.fields["ip"].initial = "api.datadoghq.com/api/v1/"
        self.fields["use_auth_headers"].initial = True
        self.fields["headers"].initial = {'api_key': '00000000000000000000000000000000',
                                          'app_key': '00000000000000000000000000000000'}
        self.fields[
            "headers"].help_text = 'You can get/create the keys from https://app.datadoghq.com/account/settings#api'
        self.fields["protocol"].initial = "https"

        # Remove connection info fields we do not need in data dog credentials
        del self.fields['ssh_key']
        del self.fields["username"]
        del self.fields["password"]
        del self.fields["port"]

        # mark all fields as required
        for field in list(self.fields.values()):
            field.required = True

    def clean(self):
        datadog = DataDog()
        response = datadog.verify_connection(
            connection_info=ConnectionInfo(
                ip=self.cleaned_data.get('ip'),
                protocol=self.cleaned_data.get('protocol'),
                headers=self.cleaned_data.get('headers')
            )
        )

        if not response[0]:
            raise forms.ValidationError(f"{response[1]}. Unable to connect to Datadog using the credentials provided."
                                        " Please enter the credentials correctly"
                                        )
        return self.cleaned_data

    def save(self, *args, **kwargs):
        credentials = super(DataDogConnectionForm, self).save(*args, **kwargs)
        return credentials
