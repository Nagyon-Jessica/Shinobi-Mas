import uuid, random, string
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
        # 管理画面にリダイレクト
        return redirect(to=f'/engawa/{e_uuid}')

class EngawaView(ListView):
    template_name = 'homaster/engawa.html'
    model = Handout