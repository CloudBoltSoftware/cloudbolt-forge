from django import forms

from common.forms import C2Form
from common.methods import mkDateTime


class DateRangeForm(C2Form):
    """
    Simple form for choosing a date range.
    """

    start_date = forms.CharField(
        label="Start Date",
        required=True,
        widget=forms.TextInput(attrs={'class': 'render_as_datepicker'}),
    )
    end_date = forms.CharField(
        label="End Date",
        required=True,
        widget=forms.TextInput(attrs={'class': 'render_as_datepicker'}),
    )

    def clean_start_date(self):
        return mkDateTime(self.cleaned_data['start_date'])

    def clean_end_date(self):
        return mkDateTime(self.cleaned_data['end_date'])

    def clean(self):
        """
        Validates posted form.
        """
        start_date = self.cleaned_data['start_date']
        end_date = self.cleaned_data['end_date']

        if (end_date - start_date).total_seconds() < 0:
            raise forms.ValidationError("Start date can't be after end date")

        return self.cleaned_data
