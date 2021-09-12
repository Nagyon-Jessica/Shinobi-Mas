import uuid, random, string
from django.urls import reverse
from django.http import Http404
from django.http.response import HttpResponseRedirect
from django.forms import fields
from django.shortcuts import redirect
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView
from django.contrib.auth import authenticate, login
from bootstrap_modal_forms.generic import BSModalFormView
from .mixins import LoginRequiredCustomMixin
from .models import *
from .forms import *
from .constants import *

def signin(request, **kwargs):
    if "p_code" in request.GET:
        p_code = request.GET.get("p_code")
    else:
        return HttpResponseRedirect('homaster:index')

    # アクセスユーザの存在確認
    player = authenticate(request, uuid=kwargs['uuid'], p_code=p_code)
    if player:
        # 存在するユーザならログイン
        login(request, player)
        request.user = player
    else:
        # ユーザが存在しなければトップページへリダイレクト
        return HttpResponseRedirect('homaster:index')
    # ハンドアウト一覧画面へ遷移
    return HttpResponseRedirect('homaster:engawa')

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
        player, _ = Player.objects.get_or_create(engawa=Engawa(uuid=e_uuid), p_code=code, gm_flag=True)

        # GMのログイン処理
        login(request, player)
        request.user = player

        # 管理画面にリダイレクト
        return HttpResponseRedirect('homaster:engawa')

class EngawaView(LoginRequiredCustomMixin, ListView):
    template_name = 'homaster/engawa.html'
    model = Handout

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        engawa = self.request.user.engawa
        player = Player.objects.get(engawa=engawa, p_code=self.request.user.p_code)
        context["engawa"] = engawa
        context['player'] = player
        # プレイヤーのロール名(GM/PCx)を判定
        if player.gm_flag:
            role_name = "GM"
        else:
            # ENGAWAに所属するplayerのリスト
            players = Player.objects.filter(engawa=engawa).order_by("id")
            pl_num = players.index(player) + 1
            role_name = f"PC{pl_num}"
        context['role_name'] = role_name
        self.request.session['role_name'] = role_name
        return context

class CreateHandoutView(LoginRequiredCustomMixin, CreateView):
    template_name = 'homaster/create.html'
    model = Handout
    fields = ['type', 'pc_name', 'pl_name', 'front', 'back']

    def get(self, request, *args, **kwargs):
        # クエリパラメータが不正の場合，自動で"1"とする
        if self.request.GET.get("type", default=None) not in ["1", "2", "3"]:
            return redirect('/create?type=1')
        else:
            return super().get(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        param = self.request.GET.get("type")
        form.fields['type'] = fields.CharField(label="ハンドアウト種別", initial=HANDOUT_TYPE_DICT[param], disabled=True)
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['role_name'] = self.request.session['role_name']
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        print(request.POST)
        return redirect('homaster:engawa')

class HandoutTypeChoiceView(BSModalFormView):
    template_name = 'homaster/type_choice_modal.html'
    form_class = HandoutTypeForm

    def post(self, request):
        type = request.POST['type']
        redirect_url = reverse('homaster:create') + f'?type={type}'
        return redirect(redirect_url)
