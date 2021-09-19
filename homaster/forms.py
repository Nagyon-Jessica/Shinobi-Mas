from django import forms
from django.forms.fields import ChoiceField, MultipleChoiceField
from django.forms.widgets import CheckboxSelectMultiple, RadioSelect
from bootstrap_modal_forms.forms import BSModalForm
from .models import Handout

class HandoutTypeForm(BSModalForm):
    type = ChoiceField(
        choices=(
            ("1", "PC"),
            ("2", "NPC"),
            ("3", "HO"),
        ),
        widget=RadioSelect
    )

class HandoutForm(forms.ModelForm):
    class Meta:
        model = Handout
        fields = ('type', 'pc_name', 'pl_name', 'front', 'back')

class AuthControlForm(BSModalForm):
    auth_front = MultipleChoiceField(label="使命(表)", required=False, widget=CheckboxSelectMultiple)
    auth_back = MultipleChoiceField(label="秘密(裏)", required=False, widget=CheckboxSelectMultiple)