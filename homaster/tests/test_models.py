from django.test import TestCase
from .factories import *

class PlayerModelTest(TestCase):
    def test_is_gm(self):
        player = PlayerFactory()
        self.assertTrue(player.is_gm)

    def test_is_not_gm(self):
        player1 = PlayerFactory(role=0)
        player2 = PlayerFactory(role=2)
        self.assertFalse(player1.is_gm)
        self.assertFalse(player2.is_gm)

class AuthModelTest(TestCase):
    def test_auth_init(self):
        """
        Authオブジェクトが辞書型のorig_auth属性を持つことのテスト
        """
        auth = AuthFactory()
        self.assertTrue(hasattr(auth, 'orig_auth'))
        self.assertTrue("auth_front" in auth.orig_auth)
        self.assertTrue("auth_back" in auth.orig_auth)
