from django.urls import path
from . import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('engawa/<uuid>/<p_code>', views.EngawaView.as_view(), name='engawa'),
    path('create-handout/<uuid>/<p_code>', views.HandoutTypeChoiceView.as_view(), name='create-handout'),
    path('create/<uuid>/<p_code>', views.CreateHandoutView.as_view(), name='create'),
]
