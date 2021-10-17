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
