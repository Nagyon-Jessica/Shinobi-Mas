from django.shortcuts import render
from django.views.generic.edit import FormView
from .forms import EngawaForm

def index(request):
    return render(request, 'homaster/index.html')

class SetupView(FormView):
    template_name = 'homaster/setup.html'
    form_class = EngawaForm