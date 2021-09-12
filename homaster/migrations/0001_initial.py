# Generated by Django 3.2 on 2021-09-11 09:02

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('p_code', models.CharField(max_length=8)),
                ('gm_flag', models.BooleanField()),
            ],
        ),
        migrations.CreateModel(
            name='Engawa',
            fields=[
                ('uuid', models.CharField(max_length=36, primary_key=True, serialize=False)),
                ('scenario_name', models.CharField(max_length=100, verbose_name='シナリオ名')),
            ],
        ),
        migrations.CreateModel(
            name='Handout',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.PositiveSmallIntegerField()),
                ('pc_name', models.CharField(blank=True, max_length=100, null=True, verbose_name='PC名')),
                ('pl_name', models.CharField(blank=True, max_length=100, null=True, verbose_name='PL名')),
                ('front', models.TextField(blank=True, max_length=1000, null=True, verbose_name='使命(表)')),
                ('back', models.TextField(blank=True, max_length=1000, null=True, verbose_name='秘密(裏)')),
                ('invitation_code', models.CharField(blank=True, max_length=8, null=True)),
                ('engawa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='homaster.engawa')),
            ],
        ),
        migrations.CreateModel(
            name='Auth',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('auth_front', models.BooleanField()),
                ('auth_back', models.BooleanField()),
                ('handout', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='homaster.handout')),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='player',
            name='engawa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='homaster.engawa'),
        ),
        migrations.AddField(
            model_name='player',
            name='handout',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='homaster.handout'),
        ),
        migrations.AddIndex(
            model_name='player',
            index=models.Index(fields=['engawa', 'p_code'], name='homaster_pl_engawa__310a31_idx'),
        ),
    ]
