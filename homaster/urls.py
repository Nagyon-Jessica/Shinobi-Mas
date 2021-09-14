from django.urls import path
from . import views

app_name = 'homaster'
urlpatterns = [
    path('index', views.IndexView.as_view(), name='index'),
    path('engawa', views.EngawaView.as_view(), name='engawa'),
    path('engawa/close', views.close_engawa, name='close-engawa'),
    path('create-handout', views.HandoutTypeChoiceView.as_view(), name='create-handout'),
    path('create', views.CreateHandoutView.as_view(), name='create'),
    path('delete', views.delete, name='delete'),
    # path('delete-handout', views.HandoutTypeChoiceView.as_view(), name='delete-handout'),
    path('<uuid>', views.signin, name='signin'),
]
