from django import forms
from django.utils.safestring import mark_safe

from utilities.forms import ConnectionInfoForm

from utilities.models import ConnectionInfo

from .office365_helper import Office365Manager


class Office365ConnectionForm(ConnectionInfoForm):
    protocol = forms.ChoiceField(
        choices=[('http', 'HTTP'), ('https', 'HTTPS')], label='Protocol')

    def __init__(self, *args, **kwargs):
        super(Office365ConnectionForm, self).__init__(*args, **kwargs)
        self.fields["name"].widget = forms.HiddenInput()
        self.fields["name"].initial = "Office365"
        self.fields["protocol"].initial = "HTTPS"
        self.fields["port"].initial = 443
        self.fields["ip"].initial = 'graph.microsoft.com'
        self.fields["use_auth_headers"].initial = True
        self.fields['headers'].initial = {'client_id': None, 'client_secret': None, 'tenant_id': None}
        self.fields["headers"].help_text = mark_safe('You can get the headers while registering an app '
                                                     'in the Azure Active Directory')

        # Remove connection info fields we do not need for office365
        del self.fields['ssh_key']
        del self.fields['username']
        del self.fields['password']

        # mark all fields as required
        for field in list(self.fields.values()):
            field.required = True

    def clean(self):
        ip = self.cleaned_data.get('ip')
        if not ip:
            raise forms.ValidationError("IP/Hostname is a required field")
        port = self.cleaned_data.get('port')
        if not port:
            raise forms.ValidationError("PORT is a required field")
        headers = self.cleaned_data.get('headers')
        if not headers:
            raise forms.ValidationError("Headers must be supplied.")

        connection_info = ConnectionInfo(
            name="Office365",
            protocol="HTTPS",
            ip='graph.microsoft.com',
            port=443
        )
        office365manager = Office365Manager(connection_info)
        ok, reason = office365manager.verify_credentials(
            self.cleaned_data.get('protocol'),
            self.cleaned_data.get('ip'),
            self.cleaned_data.get('port'),
            self.cleaned_data.get('headers'),
        )
        if not ok:
            raise forms.ValidationError(
                f"{reason}")
        return self.cleaned_data
