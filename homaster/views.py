import logging
import os
import pdb
import random
import string
import uuid
from collections import OrderedDict
from itertools import groupby
from operator import inv

from bootstrap_modal_forms.generic import BSModalFormView
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core.mail import send_mail
from django.forms import CheckboxInput, fields
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, FormView, UpdateView
from webpush import send_user_notification

from .constants import *
from .forms import *
from .mixins import LoginRequiredCustomMixin
from .models import *

logger = logging.getLogger(__name__)

def signin(request, **kwargs):
    if "p_code" in request.GET:
        p_code = request.GET.get("p_code")
    else:
        logger.error("There is not p_code in query string.")
        return redirect('homaster:index')

    # アクセスユーザの存在確認
    uuid = kwargs['uuid']
    player = authenticate(request, uuid=uuid, p_code=p_code)
    if player:
        # 仮登録のGMの場合，正式登録を行う
        if player.role == 2:
            engawa = Engawa.objects.get(uuid=uuid)
            Player.objects.filter(engawa=engawa, p_code=p_code).update(role=1)
            # 正式登録完了メールの送信
            subject = "【Shinobo-Mas】登録完了のお知らせ"
            message = f"貴方をシナリオ【{engawa.scenario_name}】のGMとして登録いたしました！\n\n"\
                      "シナリオのENGAWAへ再び出るためのURLを忘れてしまった場合は，\n"\
                      "トップページの「ENGAWAのURLを忘れてしまった場合はこちら」を\n"\
                      "クリックし，フォームにご登録いただいたメールアドレスを入力いただくと\n"\
                      "システムからメールにてURLを通知させていただきます。\n\n"\
                      "引き続きShinobi-Masをよろしくお願いいたします。\n\n"\
                      "※ このメールに心あたりがない場合は、第三者がメールアドレスの入力を誤った可能性があります。\n"\
                      "その際は、大変お手数ではございますが、メールを破棄していただきますようにお願いいたします。"
            from_email = "shinobimas.master@gmail.com"
            recipient_list = [player.email]
            try:
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
            except Exception:
                logger.exception(f"Cannot send an email to {player.email}.")
        # 存在するユーザならログイン
        login(request, player)
        request.user = player
    else:
        # ユーザが存在しなければトップページへリダイレクト
        logger.error(f"There is not a player with p_code {p_code} in ENGAWA {uuid}")
        return redirect('homaster:index')
    # ハンドアウト一覧画面へ遷移
    return redirect('homaster:engawa')

def delete(request):
    # ログインしていなければトップページにリダイレクト
    if not hasattr(request.user, "role"):
        return redirect("homaster:index")

    # ログインユーザがGMでなければエラー
    if not request.user.is_gm:
        logger.error(f"This player with p_code {request.user.p_code} is not GM.")
        raise Http404()

    ho_id = request.GET.get('id')
    # 指定したIDのハンドアウトが存在しなければエラー
    handout = get_object_or_404(Handout, id=ho_id)

    # 他のENGAWAのハンドアウトを削除しようとしていたらエラー
    if handout.engawa != request.user.engawa:
        logger.error(f"This player with p_code {request.user.p_code} cannot delete a handout(ID: {handout.id}) of other ENGAWA.")
        raise Http404()

    handout.delete()
    return redirect('homaster:engawa')

def close_engawa(request):
    """使い終わったENGAWAを削除する"""
    # ログインしていなければトップページにリダイレクト
    if not hasattr(request.user, "role"):
        return redirect("homaster:index")

    # ログインユーザがGMでなければエラー
    if not request.user.is_gm:
        logger.error(f"This player with p_code {request.user.p_code} is not GM.")
        raise Http404()
    request.user.engawa.delete()
    return redirect("homaster:close-success")

def after_close(request):
    return render(request, template_name="homaster/thanks.html")

def interim(request):
    return render(request, template_name="homaster/interim.html")

def release_notes(request):
    return render(request, template_name="homaster/release_notes.html")

class IndexView(FormView):
    template_name = 'homaster/index.html'
    form_class = IndexForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['env'] = os.environ.get('SYSTEM_ENV', None)
        return context

    def form_valid(self, form):
        scenario_name = form.cleaned_data["scenario_name"]
        email = form.cleaned_data["email"]
        if email:
            # 入力されたメールアドレスを持った正式登録済みのGMが既に存在するか
            exist = Player.objects.filter(email=email, role=1).exists()

        # ENGAWAのUUID払い出し
        e_uuid = uuid.uuid4()
        # ENGAWAを作成
        Engawa.objects.create(uuid=e_uuid, scenario_name=scenario_name)

        # p_codeの払い出し
        code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

        role = 2 if email and not exist else 1

        # GMのPlayerレコードを登録
        player, _ = Player.objects.get_or_create(engawa=Engawa(uuid=e_uuid), p_code=code, role=role, email=email)

        if not email:
            # GMのログイン処理
            login(self.request, player)
            self.request.user = player
            # 管理画面にリダイレクト
            return redirect('homaster:engawa')
        elif exist:
            # 正式登録完了メールの送信
            subject = "【Shinobo-Mas】登録完了のお知らせ"
            message = f"貴方をシナリオ【{scenario_name}】のGMとして登録いたしました！\n\n"\
                      "シナリオのENGAWAへ再び出るためのURLを忘れてしまった場合は，\n"\
                      "トップページの「ENGAWAのURLを忘れてしまった場合はこちら」を\n"\
                      "クリックし，フォームにご登録いただいたメールアドレスを入力いただくと\n"\
                      "システムからメールにてURLを通知させていただきます。\n\n"\
                      "引き続きShinobi-Masをよろしくお願いいたします。\n\n"\
                      "※ このメールに心あたりがない場合は、第三者がメールアドレスの入力を誤った可能性があります。\n"\
                      "その際は、大変お手数ではございますが、メールを破棄していただきますようにお願いいたします。"
            from_email = "shinobimas.master@gmail.com"
            recipient_list = [player.email]
            try:
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
            except Exception:
                logger.exception(f"Cannot send an email to {player.email}.")

            # GMのログイン処理
            login(self.request, player)
            self.request.user = player

            # 管理画面にリダイレクト
            return redirect('homaster:engawa')
        else:
            subject = "【Shinobo-Mas】仮登録完了のお知らせ"
            message = f"貴方をシナリオ【{scenario_name}】のGMとして仮登録いたしました！\n\n"\
                      "以下のURLより本登録を完了させてください。\n\n"\
                      f"https://{self.request.META.get('HTTP_HOST')}/{e_uuid}?p_code={code}\n\n"\
                      "※ このメールに心あたりがない場合は、第三者がメールアドレスの入力を誤った可能性があります。\n"\
                      "その際は、大変お手数ではございますが、メールを破棄していただきますようにお願いいたします。"
            from_email = "shinobimas.master@gmail.com"
            recipient_list = [email]
            try:
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
            except Exception:
                logger.exception(f"Cannot send an email to {email}.")
            # 仮登録完了画面にリダイレクト
            return redirect("homaster:interim")

class ReenterView(FormView):
    template_name = 'homaster/reenter.html'
    form_class = ReenterForm

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        accounts = Player.objects.filter(email=email, role=1)
        message = "貴方がGMを担当するシナリオのENGAWAは以下のとおりです。\n\n"
        for acc in accounts:
            message += f"{acc.engawa.scenario_name}: https://{self.request.META.get('HTTP_HOST')}/{acc.engawa.uuid}?p_code={acc.p_code}\n"
        message += "\n引き続きセッションをお楽しみください！\n\n"\
                   "※ このメールに心あたりがない場合は、第三者がメールアドレスの入力を誤った可能性があります。\n"\
                   "その際は、大変お手数ではございますが、メールを破棄していただきますようにお願いいたします。"
        subject = "【Shinobi-Mas】ENGAWA再訪URLのご通知"
        from_email = "shinobimas.master@gmail.com"
        recipient_list = [email]
        try:
            send_mail(subject, message, from_email, recipient_list)
        except Exception:
            logger.exception("Cannot send an email.")
        return redirect('homaster:reenter')

class EngawaView(LoginRequiredCustomMixin, ListView):
    template_name = 'homaster/engawa.html'
    model = Handout

    def get_queryset(self):
        engawa = self.request.user.engawa
        return Handout.objects.filter(engawa=engawa).order_by('type', 'id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['env'] = os.environ.get('SYSTEM_ENV', None)
        engawa = self.request.user.engawa
        player = Player.objects.get(engawa=engawa, p_code=self.request.user.p_code)
        context["engawa"] = engawa
        context['player'] = player
        # プレイヤーのロール名(GM/PCx)を判定
        if player.is_gm:
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
            ho_names = OrderedDict()
            for t, hos in groupby(context['object_list'], key=lambda x: x.type):
                type = HANDOUT_TYPE_DICT[str(t)]
                for i, ho in enumerate(hos):
                    ho_names[str(ho.id)] = (type + str(i + 1))
            self.request.session['ho_names'] = ho_names
            for i, (_, ho_name) in enumerate(ho_names.items()):
                context['object_list'][i].ho_name = ho_name
            if not self.request.user.is_gm:
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
        if not request.user.is_gm:
            logger.error(f"This player with p_code {request.user.p_code} is not GM.")
            raise Http404()
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
            player, _ = Player.objects.get_or_create(engawa=engawa, handout=self.object, p_code=code, role=0)
            handouts = Handout.objects.filter(engawa=engawa).order_by('id')
            for ho in handouts:
                if ho == self.object:
                    continue
                Auth.objects.create(player=player, handout=ho, auth_front=bool(not ho.hidden), auth_back=False)

        # PLが存在する場合，作成するハンドアウトについてのAuthレコードを作成する
        players = Player.objects.filter(engawa=engawa, role=0).order_by('id')
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

        return redirect(self.get_success_url())

class HandoutDetailView(LoginRequiredCustomMixin, DetailView):
    template_name = 'homaster/detail.html'
    model = Handout

    def get(self, request, *args, **kwargs):
        ho_id = kwargs['pk']
        # ログイン中のENGAWAにid=pkとなるハンドアウトがなければ404
        ho = get_object_or_404(Handout, engawa=request.user.engawa, id=ho_id)
        # ハンドアウトが非公開且つユーザがPLの場合，表の閲覧権限がなければ404
        if ho.hidden and not request.user.is_gm:
            auth = Auth.objects.get(handout=ho, player=request.user)
            if not auth.auth_front:
                raise Http404
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        handout = kwargs['object']
        context = super().get_context_data(**kwargs)

        player = self.request.user
        if player.is_gm:
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
        if not request.user.is_gm:
            logger.error(f"This player with p_code {request.user.p_code} is not GM.")
            raise Http404()
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
        return redirect(self.get_success_url())

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
    ajax_template_name = 'homaster/auth_control_modal.html'
    form_class = AuthControlForm
    success_url = reverse_lazy("homaster:engawa")

    def get_context_data(self, **kwargs):
        submit_token = set_submit_token(self.request)
        context = super().get_context_data(**kwargs)
        context['submit_token'] = submit_token

        # ハンドアウトIDとハンドアウト名の対応表
        ho_names = self.request.session['ho_names']

        engawa = self.request.user.engawa
        hos = Handout.objects.filter(engawa=engawa).order_by('type', 'id')
        # NPC/HOの場合はハンドアウト種別+PC名をテーブルヘッダに表示する
        context['ho_names'] = list(map(lambda h: ho_names[str(h.id)] if h.type == 1 else ho_names[str(h.id)] + "\n" + h.pc_name, hos))
        return context

    def get_form(self):
        form = super().get_form()
        # ハンドアウトIDとハンドアウト名の対応表
        ho_names = self.request.session['ho_names']

        # ENGAWAに属する全PL（GM以外）を取得
        user = self.request.user
        engawa = user.engawa
        players = Player.objects.filter(engawa=engawa, role=0).order_by('id')

        for pl in players:
            # PLのHO名
            ho_name = ho_names[str(pl.handout.id)]
            auths = Auth.objects.filter(player=pl).order_by('handout__type', 'handout__id')
            print(list(map(lambda a: a.handout.id, auths)))
            # フィールドを動的に生成
            # PL画面の場合チェックボックスをdisabledにする
            form.fields[ho_name + "_front"] = MultipleChoiceField(
                label=ho_name, required=False, widget=CheckboxSelectMultiple, disabled=(not user.is_gm))
            form.fields[ho_name + "_back"] = MultipleChoiceField(
                label=ho_name, required=False, widget=CheckboxSelectMultiple, disabled=(not user.is_gm))

            # フィールドに選択肢を追加
            choices = []
            for auth in auths:
                # choices.append((str(auth.id), f"{ho_names[str(auth.handout.id)]}"))
                choices.append((str(auth.id), ""))
            form.fields[ho_name + "_front"].choices = tuple(choices)
            form.fields[ho_name + "_back"].choices = tuple(choices)
            # フィールドの初期値を登録
            form.fields[ho_name + "_front"].initial = [a.id for a in auths if a.auth_front]
            form.fields[ho_name + "_back"].initial = [a.id for a in auths if a.auth_back]

        return form

    def form_valid(self, form):
        # チェックがついたAuth IDの一覧を取得
        back_choiced = list(map(lambda k: form.data.getlist(k), filter(lambda key: "_back" in key, self.request.POST.keys())))
        back_choiced = sum(back_choiced, [])
        front_choiced = list(map(lambda k: form.data.getlist(k), filter(lambda key: "_front" in key, self.request.POST.keys())))
        front_choiced = sum(front_choiced, [])
        
        # チェックボックス全体の配列
        choices = []
        for key, field in form.fields.items():
            if "_back" in key:
                choices += field._choices

        ho_names = self.request.session['ho_names']
        for choice in choices:
            auth = Auth.objects.get(id=int(choice[0]))
            kwargs = {
                "auth_front": choice[0] in front_choiced,
                "auth_back": choice[0] in back_choiced
            }
            # print(f"id: {choice[0]}, kwargs: {kwargs}, orig: {auth.orig_auth}")
            # 権限の変更があればDBを更新し，対象PLにプッシュ通知を送信
            if kwargs != auth.orig_auth:
                Auth.objects.filter(id=int(choice[0])).update(**kwargs)
                send_push(auth, ho_names[str(auth.handout.id)])
        return JsonResponse({'__all__': None})

    def form_invalid(self, form):
        error_dict = form.errors.as_data()
        # ValidationErrorにstr()を適用すると['***']のような文字列が返るので，不要な部分を削除
        error_dict['__all__'] = list(map(lambda e: str(e).strip("[]'"), error_dict['__all__']))
        # submit_tokenをセットし直すためレスポンスに含める
        token = set_submit_token(self.request)
        return JsonResponse({'err_msg': error_dict['__all__'], 'submit_token': token})

    def post(self, request):
        if not exists_submit_token(request):
            return redirect('homaster:engawa')
        return super().post(request)

class InviteView(BSModalFormView):
    template_name = 'homaster/invite_modal.html'
    form_class = HandoutTypeForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        engawa = self.request.user.engawa
        handouts = Handout.objects.filter(engawa=engawa, type=1).order_by('id')

        # ハンドアウトIDとハンドアウト名の対応表
        ho_names = self.request.session['ho_names']

        context['handouts'] = []

        for handout in handouts:
            pl_name = "匿名プレイヤー" if not handout.pl_name else handout.pl_name
            ho_name = ho_names[str(handout.id)]

            # 招待用URLを生成
            invite_url = "https://" + \
                self.request.META.get("HTTP_HOST") + \
                    reverse('homaster:signin', kwargs={"uuid": engawa.uuid}) + \
                        "?p_code=" + handout.p_code

            context['handouts'].append((pl_name, invite_url, ho_name))

        # GM再入室用URL
        gm_url = "https://" + \
            self.request.META.get("HTTP_HOST") + \
                reverse('homaster:signin', kwargs={"uuid": engawa.uuid}) + \
                    "?p_code=" + self.request.user.p_code

        context['handouts'].append(('GM', gm_url, 'GM'))

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

def send_push(auth, ho_name):
    player = auth.player
    payload = {'head': f'{ho_name}への閲覧権限が更新されました', 'body': '画面を再読込してください'}
    try:
        send_user_notification(user=player, payload=payload, ttl=1000)
    except Exception:
        logger.exception("Failed to send Webpush.")
