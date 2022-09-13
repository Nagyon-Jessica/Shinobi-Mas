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

class ReenterForm(forms.Form):
    email = EmailField(
        label="入力したメールアドレスが登録済みの場合，シナリオのURLをメールで送信します",
        required=True
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        accounts = Player.objects.filter(email=email, role=1)
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
        labels = {
            'type': "ハンドアウト種別",
            'pc_name': 'PC名',
            'pl_name': 'PL名',
            'front': '使命(表)',
            'back': '秘密(裏)'
        }

class AuthControlForm(BSModalForm):
    def clean(self):
        # print(self.has_changed())
        # 変更がなければエラーを返す
        if not self.has_changed():
            raise forms.ValidationError("変更がありません")

        cleaned_data = super(AuthControlForm, self).clean()
        # 裏だけにチェックがついているものがあればエラーを返す
        # PCx_backがPCx_frontの部分集合でなければエラー
        for k, v in cleaned_data.items():
            if "_back" in k:
                honame = k.split("_")[0]
                front = cleaned_data[f'{honame}_front']
                if not set(v).issubset(set(front)):
                    raise forms.ValidationError("裏だけを公開することはできません")

        return cleaned_data
