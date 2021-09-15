import uuid, random, string
from itertools import groupby
from django.urls import reverse, reverse_lazy
from django.http import Http404
from django.http.response import HttpResponseRedirect
from django.forms import fields, CheckboxInput
from django.shortcuts import redirect
from django.views.generic import TemplateView, ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
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
        return HttpResponseRedirect('index')

    # アクセスユーザの存在確認
    player = authenticate(request, uuid=kwargs['uuid'], p_code=p_code)
    if player:
        # 存在するユーザならログイン
        login(request, player)
        request.user = player
    else:
        # ユーザが存在しなければトップページへリダイレクト
        return HttpResponseRedirect('index')
    # ハンドアウト一覧画面へ遷移
    return HttpResponseRedirect('engawa')

def delete(request):
    ho_id = request.GET.get('id')
    Handout.objects.get(id=ho_id).delete()
    return HttpResponseRedirect('engawa')

def close_engawa(request):
    """使い終わったENGAWAを削除する"""
    request.user.engawa.delete()
    return redirect("homaster:index")

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
        return HttpResponseRedirect('engawa')

class EngawaView(LoginRequiredCustomMixin, ListView):
    template_name = 'homaster/engawa.html'
    model = Handout

    def get_queryset(self):
        engawa = self.request.user.engawa
        if self.request.user.gm_flag:
            return Handout.objects.filter(engawa=engawa).order_by('type')
        else:
            auth = Auth.objects.filter(player=self.request.user, auth_front=True)
            handouts = list(map(lambda a: a.handout, auth))
            handouts = sorted(handouts, key=lambda h: h.type)
            return handouts

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
            pl_num = list(players).index(player)
            role_name = f"PC{pl_num}"
        context['role_name'] = role_name
        self.request.session['role_name'] = role_name

        # 表示するハンドアウトが存在する場合，ハンドアウト名リストを生成
        if context['object_list']:
            ho_names = []
            for t, hos in groupby(context['object_list'], key=lambda x: x.type):
                type = HANDOUT_TYPE_DICT[str(t)]
                for i in range(len(list(hos))):
                    ho_names.append(type + str(i + 1))
            for i, ho_name in enumerate(ho_names):
                context['object_list'][i].ho_name = ho_name
        return context

class CreateHandoutView(LoginRequiredCustomMixin, CreateView):
    template_name = 'homaster/create.html'
    model = Handout
    fields = ['pc_name', 'pl_name', 'hidden', 'front', 'back']
    success_url = reverse_lazy("homaster:engawa")

    def get(self, request, *args, **kwargs):
        # クエリパラメータが不正の場合，自動で"1"とする
        if self.request.GET.get("type", default=None) not in ["1", "2", "3"]:
            return redirect('/create?type=1')
        else:
            return super().get(request, *args, **kwargs)

    def get_form(self):
        form = super().get_form()
        ho_type = self.request.GET.get("type", default=None)
        if ho_type == "1":
            form.fields['hidden'].widget = forms.HiddenInput()
        else:
            form.fields['hidden'] = fields.BooleanField(
                label="非公開（シナリオ開始時には表を含め公開されません）",
                required=False,
                widget=CheckboxInput(attrs={'class': 'check'})
            )
        return form

    def get_context_data(self, **kwargs):
        param = self.request.GET.get("type")
        context = super().get_context_data(**kwargs)
        context['role_name'] = self.request.session['role_name']
        context['ho_type'] = HANDOUT_TYPE_DICT[param]
        return context

    def form_valid(self, form):
        handout = form.save(commit=False)
        ho_type = self.request.GET.get("type", default=None)
        engawa = self.request.user.engawa
        is_pc = (ho_type == "1")
        if is_pc:
            # p_codeの払い出し
            code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        else:
            code = ""
        handout.engawa_id = engawa.uuid
        handout.type = int(ho_type)
        handout.p_code = code
        self.object = form.save()

        # PCを作成する場合，紐づくPLと，そのPLの既存ハンドアウトに対する権限レコードを作成する
        if is_pc:
            player, _ = Player.objects.get_or_create(engawa=engawa, handout=self.object, p_code=code, gm_flag=False)
            handouts = Handout.objects.filter(engawa=engawa)
            for ho in handouts:
                if ho == self.object:
                    continue
                Auth.objects.create(player=player, handout=ho, auth_front=bool(not ho.hidden), auth_back=False)

        # PLが存在する場合，作成するハンドアウトについてのAuthレコードを作成する
        players = Player.objects.filter(engawa=engawa, gm_flag=False)
        is_hidden = getattr(handout, 'hidden', False)
        if is_pc:
            # PCの場合，PLがハンドアウトの所有者の時のみ裏を公開
            for pl in players:
                is_owner = (pl.handout == self.object)
                Auth.objects.create(player=pl, handout=self.object, auth_front=True, auth_back=is_owner)
        else:
            # PC以外の場合，「非公開」にチェックが入った時のみ表も非公開
            for pl in players:
                Auth.objects.create(player=pl, handout=self.object, auth_front=(not is_hidden), auth_back=False)

        return HttpResponseRedirect(self.get_success_url())

class HandoutDetailView(LoginRequiredCustomMixin, DetailView):
    template_name = 'homaster/detail.html'
    model = Handout

    def get_context_data(self, **kwargs):
        handout = kwargs['object']
        context = super().get_context_data(**kwargs)

        player = self.request.user
        if player.gm_flag:
            context['allowed'] = True
        else:
            auth = Auth.objects.get(handout=handout, player=player)
            context['allowed'] = auth.auth_back

        context['role_name'] = self.request.session['role_name']
        context['ho_type'] = HANDOUT_TYPE_DICT[str(handout.type)]
        context['handout'] = handout
        return context

class UpdateHandoutView(LoginRequiredCustomMixin, UpdateView):
    template_name = 'homaster/update.html'
    model = Handout
    fields = ['pc_name', 'pl_name', 'hidden', 'front', 'back']
    success_url = reverse_lazy("homaster:engawa")

    def get_form(self):
        form = super().get_form()
        ho_type = self.object.type
        if ho_type == 1:
            form.fields['hidden'].widget = forms.HiddenInput()
        else:
            form.fields['hidden'] = fields.BooleanField(
                label="非公開（シナリオ開始時には表を含め公開されません）",
                required=False,
                widget=CheckboxInput(attrs={'class': 'check'})
            )
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['role_name'] = self.request.session['role_name']
        ho_type = context['object'].type
        context['ho_type'] = HANDOUT_TYPE_DICT[str(ho_type)]
        return context

    def form_valid(self, form):
        ho_after = form.save(commit=False)
        ho_before = Handout.objects.get(id=ho_after.id)
        # hiddenが変わる場合は紐づくAuthのauth_frontも更新
        if ho_after.hidden != ho_before.hidden:
            Auth.objects.filter(handout=ho_before).update(auth_front=(not ho_after.hidden))
        self.object = form.save()
        return HttpResponseRedirect(self.get_success_url())

class HandoutTypeChoiceView(BSModalFormView):
    template_name = 'homaster/type_choice_modal.html'
    form_class = HandoutTypeForm

    def post(self, request):
        type = request.POST['type']
        redirect_url = reverse('homaster:create') + f'?type={type}'
        return redirect(redirect_url)

class InviteView(BSModalFormView):
    template_name = 'homaster/invite_modal.html'
    form_class = HandoutTypeForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ho_id = self.request.GET.get('id')
        handout = Handout.objects.get(id=ho_id)
        if not handout.pl_name:
            handout.pl_name = "匿名プレイヤー"

        # 招待用URLを生成
        invite_url = "http://" + \
            self.request.META.get("HTTP_HOST") + \
                reverse('homaster:signin', kwargs={"uuid": handout.engawa.uuid}) + \
                    "?p_code=" + handout.p_code

        context['handout'] = handout
        context['invite_url'] = invite_url
        return context
