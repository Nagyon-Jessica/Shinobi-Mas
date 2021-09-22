import logging
from django import forms
from django.core.mail import send_mail
from django.forms.fields import CharField, ChoiceField, EmailField, MultipleChoiceField
from django.forms.widgets import CheckboxSelectMultiple, RadioSelect
from bootstrap_modal_forms.forms import BSModalForm
from .models import Handout, Player

class IndexForm(forms.Form):
    scenario_name = CharField(label="シナリオ名を入力してください", required=True, max_length=100)
    email = EmailField(
        label="メールアドレス（ENGAWAへ出直す時に使います。登録は任意です）",
        required=False
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        if email:
            subject = "test"
            message = "sample"
            from_email = "tomono@example.com"
            recipient_list = [email]
            try:
                ret = send_mail(subject, message, from_email, recipient_list)
            except Exception as e:
                logging.exception("Cannot send an email.")
                raise forms.ValidationError("メールを送信できませんでした。正しいメールアドレスを入力してください")
            if ret < 1:
                raise forms.ValidationError("メールを送信できませんでした。正しいメールアドレスを入力してください")
        return email

class ReenterForm(forms.Form):
    email = EmailField(
        label="入力したメールアドレスが登録済みの場合，シナリオのURLをメールで送信します",
        required=True
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        accounts = Player.objects.filter(email=email, gm_flag=True)
        if not accounts:
            raise forms.ValidationError("このメールアドレスは登録されていません")
        return email

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