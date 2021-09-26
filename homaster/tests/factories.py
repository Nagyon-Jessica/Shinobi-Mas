import factory, uuid

from homaster.models import *

class EngawaFactory(factory.Factory):
    class Meta:
        model = Engawa

    uuid = uuid.uuid4()
    scenario_name = factory.Sequence(lambda n: "test%04d" % n)

class HandoutFactory(factory.Factory):
    class Meta:
        model = Handout

    engawa = factory.SubFactory(EngawaFactory)
    type = 1
    hidden = None
    pc_name = factory.Sequence(lambda n: "pc%04d" % n)
    pl_name = factory.Sequence(lambda n: "pl%04d" % n)
    front = "omote"
    back = "ura"
    p_code = "12345678"

class PlayerFactory(factory.Factory):
    class Meta:
        model = Player

    email = "test@example.com"
    engawa = factory.LazyAttribute(lambda obj: obj.handout.engawa)
    handout = factory.SubFactory(HandoutFactory)
    p_code = factory.LazyAttribute(lambda obj: obj.handout.p_code)
    role = 1

class AuthFactory(factory.Factory):
    class Meta:
        model = Auth

    player = factory.SubFactory(PlayerFactory)
    handout = factory.LazyAttribute(lambda obj: obj.player.handout)
    auth_front = True
    auth_back = False