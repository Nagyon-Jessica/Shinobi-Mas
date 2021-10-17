import factory

from homaster.models import *

class EngawaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Engawa
        django_get_or_create = ('uuid',)

    uuid = factory.Faker("uuid4")
    scenario_name = factory.Sequence(lambda n: "test%04d" % n)

class HandoutFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Handout

    engawa = factory.SubFactory(EngawaFactory)
    type = 1
    hidden = None
    pc_name = factory.Faker("first_name")
    pl_name = factory.Faker("last_name")
    front = factory.Faker("address")
    back = factory.Faker("company")
    p_code = factory.Sequence(lambda n: "%08d" % n)

class PlayerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Player

    email = "test@example.com"
    engawa = factory.LazyAttribute(lambda obj: obj.handout.engawa)
    handout = factory.SubFactory(HandoutFactory)
    p_code = factory.LazyAttribute(lambda obj: obj.handout.p_code)
    role = 1

class AuthFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Auth

    player = factory.SubFactory(PlayerFactory)
    handout = factory.LazyAttribute(lambda obj: obj.player.handout)
    auth_front = True
    auth_back = False