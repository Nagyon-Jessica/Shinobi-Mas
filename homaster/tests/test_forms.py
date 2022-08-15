from django.test import TestCase

from .factories import *
from homaster.forms import *

class ReenterFormTest(TestCase):
    def test_clean_email_ok(self):
        PlayerFactory()
        form = ReenterForm(data={"email": "test@example.com"})
        self.assertTrue(form.is_valid())

    def test_clean_email_ng(self):
        """
        入力したメールアドレスを持つ正式登録済みのGMが存在しなければ，
        バリデーションエラーになりエラーメッセージが返される
        """
        # PL
        PlayerFactory(role=0, email=None)
        # アドレスの異なるGM
        PlayerFactory(role=1, email="tomono@example.com")
        # アドレスはマッチするが仮登録のGM
        PlayerFactory(role=2)
        form = ReenterForm(data={"email": "test@example.com"})
        self.assertFalse(form.is_valid())
        self.assertTrue("このメールアドレスは登録されていません" in form.errors['email'])

class AuthControlFormTest(TestCase):
    def test_clean_ok(self):
        form = AuthControlForm(data={"PC1_front": [1], "PC1_back": []})
        form.fields["PC1_front"] = MultipleChoiceField(
            label='PC1',
            required=False,
            widget=CheckboxSelectMultiple,
            choices=[('1', '')],
            initial=['1'])
        form.fields["PC1_back"] = MultipleChoiceField(
            label='PC1',
            required=False,
            widget=CheckboxSelectMultiple,
            choices=[('1', '')],
            initial=['1'])
        self.assertTrue(form.is_valid())

    def test_clean_ng_no_change(self):
        """
        更新がひとつもない場合はエラー
        """
        form = AuthControlForm(data={"PC1_front": [1], "PC1_back": [1]})
        form.fields["PC1_front"] = MultipleChoiceField(
            label='PC1',
            required=False,
            widget=CheckboxSelectMultiple,
            choices=[('1', '')],
            initial=['1'])
        form.fields["PC1_back"] = MultipleChoiceField(
            label='PC1',
            required=False,
            widget=CheckboxSelectMultiple,
            choices=[('1', '')],
            initial=['1'])
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['__all__'][0], '変更がありません')

    def test_clean_ng_only_back_open(self):
        """
        裏のみ公開にしようとしている場合はエラー
        """
        form = AuthControlForm(data={"PC1_front": [], "PC1_back": [1]})
        form.fields["PC1_front"] = MultipleChoiceField(
            label='PC1',
            required=False,
            widget=CheckboxSelectMultiple,
            choices=[('1', '')],
            initial=['1'])
        form.fields["PC1_back"] = MultipleChoiceField(
            label='PC1',
            required=False,
            widget=CheckboxSelectMultiple,
            choices=[('1', '')],
            initial=['1'])
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['__all__'][0], '裏だけを公開することはできません')
