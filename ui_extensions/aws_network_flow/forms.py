from django import forms
from common.forms import C2Form, ProfileModelMultipleChoiceField, C2HorizontalFormHelper
from common.widgets import SelectizeMultiple
from django.utils.translation import ugettext as _


class AWSNetFlowFilterForm(C2Form):
    """
    The form for creating fields for filters on the AWS Net Flow DataTable.
    This form is not submitted! Data is picked off the page (see history/views.py)
    and the date fields are validated in JS (see c2/datepicker.js).
    This form provides internationalized label text.
    """
    startTime = forms.DateField(
        widget=forms.TextInput(attrs={'id': 'start',
                                      'name': 'start',
                                      'class': 'form-control',
                                      'placeholder': _("Start Date")
                                      }),
        label="Filter by Date",
        required=False)
    endTime = forms.DateField(
        widget=forms.TextInput(attrs={'id': 'end',
                                      'name': 'end',
                                      'class': 'form-control',
                                      'placeholder': _("End Date")
                                      }),
        required=False)
    filterPattern = forms.CharField(
        widget=forms.TextInput(attrs={'id': 'filter',
                                      'name': 'filter',
                                      'class': 'form-control',
                                      'placeholder': _("Filter on any field")
                                      }),
        label=_("Filter Pattern"),
        required=False)
    logStreamNames = forms.MultiValueField(
        widget=SelectizeMultiple(
            choices=[],
            attrs={}
        ),
        required=True
    )

    def __init__(self, *args, **kwargs):
        stream_options = kwargs.pop("stream_options")
        super().__init__(*args, **kwargs)
        self.helper = C2HorizontalFormHelper(label_cols=3, field_cols=9)
        stream_options = [(stream_option, stream_option) for stream_option in stream_options]
        self.fields["logStreamNames"].widget.choices = stream_options

