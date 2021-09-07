from django.urls import path

from . import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('engawa/<uuid>', views.EngawaView.as_view(), name='engawa'),
]