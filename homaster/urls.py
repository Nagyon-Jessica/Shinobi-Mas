from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('setup', views.SetupView.as_view(), name='setup'),
]