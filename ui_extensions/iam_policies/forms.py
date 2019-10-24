import json

from django import forms
from django.utils.translation import ugettext as _, ugettext_lazy as _lazy

from common.fields import form_field_for_cf
from common.forms import C2Form
from infrastructure.models import CustomField
from orders.models import CustomFieldValue
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


class AWSIAMPolicyForm(C2Form):
    name = forms.CharField()
    policy_document = forms.FileField(
        label='Policy Document',
        help_text=('Upload the policy document you would like to add. Document must be JSON format.')
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'cols': 20}),
        label='Description',
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.handler = kwargs.pop('handler')
        super(AWSIAMPolicyForm, self).__init__(*args, **kwargs)

    def clean(self):
        json_file = self.cleaned_data.pop('policy_document')
        try:
            json_data = json.load(json_file)
        except (AttributeError, ValueError) as ex:
            raise forms.ValidationError("Invalid JSON: {}".format(ex))

        self.cleaned_data['policy_document'] = json.dumps(json_data)

    def save(self):
        policy_name = self.cleaned_data.get('name')
        description = self.cleaned_data.get('description')
        policy_document = self.cleaned_data.get('policy_document', 'Created from CloudBolt')

        handler = self.handler
        wrapper = handler.get_api_wrapper()
        iam_client = wrapper.get_boto3_client('iam', handler.serviceaccount, handler.servicepasswd, None)

        response = iam_client.create_policy(
            PolicyName=policy_name,
            PolicyDocument=policy_document,
            Description=description,
        )

        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            msg = _("Added IAM Policy '{policy}' to '{handler}'")

        return True, msg.format(policy=policy_name, handler=handler.name)
