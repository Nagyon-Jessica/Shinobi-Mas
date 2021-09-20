import uuid, random, string
from itertools import groupby
from django.urls import reverse, reverse_lazy
from django.core.mail import send_mail
from django.http import Http404
from django.http.response import HttpResponseRedirect
from django.forms import fields, CheckboxInput
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import TemplateView, ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, FormView, UpdateView
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
    # ログインユーザがGMでなければエラー
    if not request.user.gm_flag:
        raise Http404("権限がありません")

    ho_id = request.GET.get('id')
    # 指定したIDのハンドアウトが存在しなければエラー
    handout = get_object_or_404(Handout, id=ho_id)

    # 他のENGAWAのハンドアウトを削除しようとしていたらエラー
    if handout.engawa != request.user.engawa:
        raise Http404("権限がありません")

    handout.delete()
    return HttpResponseRedirect('engawa')

def close_engawa(request):
    """使い終わったENGAWAを削除する"""
    # ログインユーザがGMでなければエラー
    if not request.user.gm_flag:
        raise Http404("権限がありません")
    request.user.engawa.delete()
    return redirect("homaster:close-success")

def after_close(request):
    return render(request, template_name="homaster/thanks.html")

class IndexView(FormView):
    template_name = 'homaster/index.html'
    form_class = IndexForm

    def form_valid(self, form):
        scenario_name = form.cleaned_data["scenario_name"]
        email = form.cleaned_data["email"]

        # ENGAWAのUUID払い出し
        e_uuid = uuid.uuid4()
        # ENGAWAを作成
        Engawa.objects.create(uuid=e_uuid, scenario_name=scenario_name)

        # p_codeの払い出し
        code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        # GMのPlayerレコードを登録
        player, _ = Player.objects.get_or_create(engawa=Engawa(uuid=e_uuid), p_code=code, gm_flag=True, email=email)

        # GMのログイン処理
        login(self.request, player)
        self.request.user = player

        # 管理画面にリダイレクト
        return HttpResponseRedirect('engawa')

class ReenterView(FormView):
    template_name = 'homaster/reenter.html'
    form_class = ReenterForm

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        accounts = Player.objects.filter(email=email, gm_flag=True)
        message = "貴方がGMを担当するシナリオのENGAWAは以下のとおりです。\n"
        for acc in accounts:
            message += f"{acc.engawa.scenario_name}: http://{self.request.META.get('HTTP_HOST')}/{acc.engawa.uuid}?p_code={acc.p_code}\n"
        subject = "test"
        from_email = "tomono@example.com"
        recipient_list = [email]
        send_mail(subject, message, from_email, recipient_list)
        return redirect('homaster:reenter')

class EngawaView(LoginRequiredCustomMixin, ListView):
    template_name = 'homaster/engawa.html'
    model = Handout

    def get_queryset(self):
        engawa = self.request.user.engawa
        return Handout.objects.filter(engawa=engawa).order_by('type')

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
        # ユーザがGMでない場合，ハンドアウト名を紐付けた後で非公開ハンドアウトを除外
        if context['object_list']:
            ho_names = []
            for t, hos in groupby(context['object_list'], key=lambda x: x.type):
                type = HANDOUT_TYPE_DICT[str(t)]
                for i in range(len(list(hos))):
                    ho_names.append(type + str(i + 1))
            self.request.session['ho_names'] = ho_names
            for i, ho_name in enumerate(ho_names):
                context['object_list'][i].ho_name = ho_name
            if not self.request.user.gm_flag:
                auths = Auth.objects.filter(player=self.request.user, auth_front=True)
                allowed_ho_ids = list(map(lambda a: a.handout.id, auths))
                context['object_list'] = list(filter(lambda h: h.id in allowed_ho_ids, context['object_list']))
        return context

class CreateHandoutView(LoginRequiredCustomMixin, CreateView):
    template_name = 'homaster/create.html'
    model = Handout
    fields = ['pc_name', 'pl_name', 'hidden', 'front', 'back']
    success_url = reverse_lazy("homaster:engawa")

    def get(self, request, *args, **kwargs):
        if not request.user.gm_flag:
            raise Http404("権限がありません")
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

    def get(self, request, *args, **kwargs):
        ho_id = kwargs['pk']
        get_object_or_404(Handout, engawa=request.user.engawa, id=ho_id)
        return super().get(request, *args, **kwargs)

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

    def get(self, request, *args, **kwargs):
        if not request.user.gm_flag:
            raise Http404("権限がありません")
        ho_id = kwargs['pk']
        get_object_or_404(Handout, engawa=request.user.engawa, id=ho_id)
        return super().get(request, *args, **kwargs)

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

class ConfirmCloseView(BSModalFormView):
    template_name = 'homaster/close_confirm_modal.html'
    form_class = HandoutTypeForm

    def get_context_data(self, **kwargs):
        submit_token = set_submit_token(self.request)
        context = super().get_context_data(**kwargs)
        context['submit_token'] = submit_token
        return context

    def post(self, request):
        if not exists_submit_token(request):
            return redirect('homaster:close-success')
        return redirect('homaster:close')

class HandoutTypeChoiceView(BSModalFormView):
    template_name = 'homaster/type_choice_modal.html'
    form_class = HandoutTypeForm

    def post(self, request):
        type = request.POST['type']
        redirect_url = reverse('homaster:create') + f'?type={type}'
        return redirect(redirect_url)

class AuthControlView(BSModalFormView):
    template_name = 'homaster/auth_control_modal.html'
    form_class = AuthControlForm
    success_url = reverse_lazy("homaster:engawa")

    def get_context_data(self, **kwargs):
        ho_name = self.request.GET.get('name')
        ho_id = self.request.GET.get('id')
        handout = Handout.objects.get(id=ho_id)
        context = super().get_context_data(**kwargs)
        context['ho_name'] = ho_name
        context['pc_name'] = handout.pc_name
        return context

    def get_form(self):
        form = super().get_form()
        ho_id = self.request.GET.get('id')
        handout = Handout.objects.get(id=ho_id)
        auths = Auth.objects.filter(handout=handout)
        ho_names = self.request.session['ho_names']
        choices_front = []
        choices_back = []
        if handout.hidden:
            # 非公開＝NPC/HOなので自身を含む場合を考慮する必要なし
            for i, auth in enumerate(auths):
                pc_name = auth.player.handout.pc_name
                if not pc_name:
                    pc_name = "未指定"
                choices_front.append((str(auth.id), f"{ho_names[i]}({pc_name})"))
                choices_back.append((str(auth.id), f"{ho_names[i]}({pc_name})"))
            form.fields['auth_front'].choices = tuple(choices_front)
            form.fields['auth_front'].initial = [a.id for a in auths if a.auth_front]
            form.fields['auth_back'].choices = tuple(choices_back)
            form.fields['auth_back'].initial = [a.id for a in auths if a.auth_back]
        else:
            del form.fields['auth_front']
            for i, auth in enumerate(auths):
                # PCの場合自身を選択肢に含めない
                if auth.handout.id != auth.player.handout.id:
                    pc_name = auth.player.handout.pc_name
                    if not pc_name:
                        pc_name = "未指定"
                    choices_back.append((str(auth.id), f"{ho_names[i]}({pc_name})"))
            form.fields['auth_back'].choices = tuple(choices_back)
            form.fields['auth_back'].initial = [a.id for a in auths if a.handout.id != a.player.handout.id and a.auth_back]
        return form

    def form_valid(self, form):
        choices = form.fields['auth_back']._choices
        for choice in choices:
            kwargs = {}
            # 裏が公開なら自動的に表も公開と決まる
            if choice[0] in self.request.POST.getlist("auth_back"):
                kwargs = {"auth_front": True, "auth_back": True}
            else:
                kwargs['auth_back'] = False
                if 'auth_front' in form.fields.keys():
                    kwargs['auth_front'] = choice[0] in self.request.POST.getlist("auth_front")
            Auth.objects.filter(id=int(choice[0])).update(**kwargs)
        return redirect("homaster:engawa")

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

class ConfirmDeleteView(BSModalFormView):
    template_name = 'homaster/delete_confirm_modal.html'
    form_class = HandoutTypeForm

    def get_context_data(self, **kwargs):
        ho_id = self.request.GET.get('id')
        handout = Handout.objects.get(id=ho_id)
        ho_name = self.request.GET.get('name')
        submit_token = set_submit_token(self.request)
        context = super().get_context_data(**kwargs)
        context['handout'] = handout
        context['ho_name'] = ho_name
        context['submit_token'] = submit_token
        return context

    def post(self, request):
        if not exists_submit_token(request):
            return redirect('homaster:engawa')
        ho_id = request.GET.get('id')
        redirect_url = reverse('homaster:delete') + f'?id={ho_id}'
        return redirect(redirect_url)

def set_submit_token(request):
    submit_token = str(uuid.uuid4())
    request.session['submit_token'] = submit_token
    return submit_token

def exists_submit_token(request):
    token_in_request = request.POST.get('submit_token')
    token_in_session = request.session.pop('submit_token', '')

    if not token_in_request:
        return False
    if not token_in_session:
        return False

    return token_in_request == token_in_session
