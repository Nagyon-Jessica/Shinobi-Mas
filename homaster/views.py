import uuid, random, string
from django.http import Http404
from django.shortcuts import redirect
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import FormView
from .models import *

class IndexView(TemplateView):
    template_name = 'homaster/index.html'

    def post(self, request):
        data = request.POST

        # ENGAWAのUUID払い出し
        e_uuid = uuid.uuid4()
        # ENGAWAを作成
        Engawa.objects.create(uuid=e_uuid, scenario_name=data['scenario_name'])

        # p_codeの払い出し
        code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        # GMのPlayerレコードを登録
        Player.objects.create(engawa=Engawa(uuid=e_uuid), p_code=code, gm_flag=True)

        # 管理画面にリダイレクト
        return redirect(to=f'/engawa/{e_uuid}/{code}')

class EngawaView(ListView):
    template_name = 'homaster/engawa.html'
    model = Handout

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["scenario_name"] = self.engawa.scenario_name
        # プレイヤーのロール名(GM/PCx)を判定
        if self.player.gm_flag:
            context["role_name"] = "GM"
        else:
            # ENGAWAに所属するplayerのリスト
            players = Player.objects.filter(engawa=self.engawa).order_by("id")
            pl_num = players.index(self.player) + 1
            context['role_name'] = f"PC{pl_num}"
        return context

    def get(self, *args, **kwargs):
        # uuidかp_codeが不正な値の場合はトップページにリダイレクト
        uuid = kwargs['uuid']
        p_code = kwargs['p_code']
        print(p_code)
        try:
            engawa = Engawa.objects.get(uuid=uuid)
        except Engawa.DoesNotExist:
            engawa = None
        try:
            player = Player.objects.get(engawa=engawa, p_code=p_code)
        except Player.DoesNotExist:
            player = None

        if not (engawa and player):
            return redirect('index')

        self.engawa = engawa
        self.player = player

        return super().get(*args, **kwargs)