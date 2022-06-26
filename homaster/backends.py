from django.contrib.auth.backends import ModelBackend
from .models import Player, Engawa

class PlayerAuthBackend(ModelBackend):
    def authenticate(self, request, uuid=None, p_code=None):
    # def authenticate(self, uuid=None, p_code=None):
        # Check the username/password and return a user.
        try:
            player = Player.objects.get(engawa=Engawa(uuid=uuid), p_code=p_code)
        except Player.DoesNotExist:
            return None
        return player
