
from django import forms
from django.utils.translation import ugettext_lazy as _lazy
from common.forms import C2Form
from common.widgets import SelectizeSelect


class GuessForm(C2Form):
    first_4 = forms.CharField(widget=forms.HiddenInput(), required=False)
    guess = forms.ChoiceField(
        label='',
    )

    def __init__(self, *args, **kwargs):
        self.game = kwargs.pop('game')
        super().__init__(*args, **kwargs)
        self.fields['first_4'].initial = self.game.first_four
        self.fields['guess'].choices = self.game.get_guess_choices()