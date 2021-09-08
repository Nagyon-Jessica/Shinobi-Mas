from django.db import models

class Engawa(models.Model):
    uuid = models.CharField(max_length=36, primary_key=True)
    scenario_name = models.CharField(max_length=255)

class Handout(models.Model):
    engawa = models.ForeignKey(Engawa, on_delete=models.CASCADE, db_index=True)
    type = models.PositiveSmallIntegerField()
    pc_name = models.CharField(max_length=255, blank=True)
    pl_name = models.CharField(max_length=255, blank=True)
    front = models.CharField(max_length=1023, blank=True)
    back = models.CharField(max_length=1023, blank=True)
    invitation_code = models.CharField(max_length=8, blank=True)

class Player(models.Model):
    engawa = models.ForeignKey(Engawa, on_delete=models.CASCADE)
    p_code = models.CharField(max_length=8)
    gm_flag = models.BooleanField()

    class Meta:
        indexes = [
            models.Index(fields=['engawa', 'p_code'])
        ]

class Auth(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, db_index=True)
    handout = models.ForeignKey(Handout, on_delete=models.CASCADE)
    auth_front = models.BooleanField()
    auth_back = models.BooleanField()