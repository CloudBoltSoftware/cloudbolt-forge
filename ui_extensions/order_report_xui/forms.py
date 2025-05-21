from django import forms
from common.forms import C2Form
from common.methods import mkDateTime
from datetime import datetime, timedelta

class SummaryRangeForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(SummaryRangeForm, self).__init__(*args, **kwargs)

        now = datetime.now()
        options = [
            ("30d", "Last 30 Days"),
            ("12m", "Last 12 Months"),
            ("all", "All Time"),
        ]

        for i in range(12):
            month = (now - timedelta(days=i*30)).replace(day=1)
            label = month.strftime("%B %Y")  # e.g., "April 2025"
            value = month.strftime("month-%Y-%m")  # e.g., "month-2025-04"
            options.append((value, label))

        self.fields['range'] = forms.ChoiceField(
            choices=options,
            required=False,
            label="Time Range",
            widget=forms.Select(attrs={'onchange': 'this.form.submit();'})
        )

class OrderRangeForm(C2Form):
    STATUS_CHOICES = [
        ("SUCCESS", "SUCCESS"),
        ("FAILURE", "FAILURE"),
        ("DENIED", "DENIED")
    ]

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

    status = forms.MultipleChoiceField(
        label="Status Filter",
        required=True,
        widget=forms.CheckboxSelectMultiple,
        choices=STATUS_CHOICES,
    )

    def clean_start_date(self):
        raw = self.cleaned_data['start_date']
        return mkDateTime(str(raw).split(" ")[0])

    def clean_end_date(self):
        raw = self.cleaned_data['end_date']
        return mkDateTime(str(raw).split(" ")[0])

    def clean_status(self):
        return self.cleaned_data['status']

    def clean(self):
        start_date = self.cleaned_data['start_date']
        end_date = self.cleaned_data['end_date']

        if (end_date - start_date).total_seconds() < 0:
            raise forms.ValidationError("Start date can't be after end date")

        return self.cleaned_data
