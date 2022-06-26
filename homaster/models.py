import uuid
from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager

# class MyManager(BaseUserManager):
#     pass

class Engawa(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scenario_name = models.CharField(verbose_name="シナリオ名", max_length=100)

class Handout(models.Model):
    engawa = models.ForeignKey(Engawa, on_delete=models.CASCADE, db_index=True, editable=False)
    type = models.PositiveSmallIntegerField()
    hidden = models.BooleanField(verbose_name="非公開", null=True, blank=True)
    pc_name = models.CharField(verbose_name="PC名", max_length=100, null=True, blank=True)
    pl_name = models.CharField(verbose_name="PL名", max_length=100, null=True, blank=True)
    front = models.TextField(verbose_name="使命(表)", max_length=1000, null=True, blank=True)
    back = models.TextField(verbose_name="秘密(裏)", max_length=1000, null=True, blank=True)
    p_code = models.CharField(max_length=8, null=True, blank=True, editable=False)

class Player(AbstractBaseUser):
    email = models.EmailField(verbose_name="メールアドレス", null=True, blank=True)
    engawa = models.ForeignKey(Engawa, on_delete=models.CASCADE, editable=False)
    handout = models.OneToOneField(Handout, on_delete=models.CASCADE, null=True, blank=True, editable=False)
    p_code = models.CharField(max_length=8, editable=False)
    role = models.PositiveSmallIntegerField(default=0)

    USERNAME_FIELD = 'id'

    class Meta:
        indexes = [
            models.Index(fields=['engawa', 'p_code'])
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["engawa", "p_code"],
                name="pl_unique"
            )
        ]

    @property
    def is_gm(self):
        return self.role == 1

class Auth(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, db_index=True, editable=False)
    handout = models.ForeignKey(Handout, on_delete=models.CASCADE, editable=False)
    auth_front = models.BooleanField()
    auth_back = models.BooleanField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["player", "handout"],
                name="auth_unique"
            )
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.orig_auth = {"auth_front": self.auth_front, "auth_back": self.auth_back}