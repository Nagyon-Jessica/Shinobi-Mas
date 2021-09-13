from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager

class MyManager(BaseUserManager):
    pass

class Engawa(models.Model):
    uuid = models.CharField(max_length=36, primary_key=True)
    scenario_name = models.CharField(verbose_name="シナリオ名", max_length=100)

class Handout(models.Model):
    engawa = models.ForeignKey(Engawa, on_delete=models.CASCADE, db_index=True)
    type = models.PositiveSmallIntegerField()
    hidden = models.BooleanField(verbose_name="非公開", null=True, blank=True)
    pc_name = models.CharField(verbose_name="PC名", max_length=100, null=True, blank=True)
    pl_name = models.CharField(verbose_name="PL名", max_length=100, null=True, blank=True)
    front = models.TextField(verbose_name="使命(表)", max_length=1000, null=True, blank=True)
    back = models.TextField(verbose_name="秘密(裏)", max_length=1000, null=True, blank=True)
    p_code = models.CharField(max_length=8, null=True, blank=True)

class Player(AbstractBaseUser):
    engawa = models.ForeignKey(Engawa, on_delete=models.CASCADE)
    handout = models.OneToOneField(Handout, on_delete=models.CASCADE, null=True, blank=True)
    p_code = models.CharField(max_length=8)
    gm_flag = models.BooleanField()

    USERNAME_FIELD = 'id'

    class Meta:
        indexes = [
            models.Index(fields=['engawa', 'p_code'])
        ]

class Auth(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, db_index=True)
    handout = models.ForeignKey(Handout, on_delete=models.CASCADE)
    auth_front = models.BooleanField()
    auth_back = models.BooleanField()
