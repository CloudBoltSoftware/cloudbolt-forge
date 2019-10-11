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
    policy_document = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 16, 'cols': 70}),
        label='Policy Document',
        help_text=('Paste the policy document you would like to add in JSON format.')
    )

    def __init__(self, *args, **kwargs):
        self.handler = kwargs.pop('handler')
        super(AWSIAMPolicyForm, self).__init__(*args, **kwargs)

    def save(self):
        policy_name = self.cleaned_data.get('name')
        policy_document = self.cleaned_data.get('policy_document')

        handler = self.handler
        wrapper = handler.get_api_wrapper()
        iam_client = wrapper.get_boto3_client('iam', handler.serviceaccount, handler.servicepasswd, None)

        response = iam_client.create_policy(
            PolicyName=policy_name,
            PolicyDocument=policy_document,
        )

        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            msg = _("Added IAM Policy '{policy}' to '{handler}'")

        return True, msg.format(policy=policy_name, handler=handler.name)
