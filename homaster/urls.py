from django.urls import path
from . import views

app_name = 'homaster'
urlpatterns = [
    path('index', views.IndexView.as_view(), name='index'),
    path('engawa', views.EngawaView.as_view(), name='engawa'),
    path('close-engawa', views.ConfirmCloseView.as_view(), name='close-engawa'),
    path('close', views.close_engawa, name='close'),
    path('create-handout', views.HandoutTypeChoiceView.as_view(), name='create-handout'),
    path('create', views.CreateHandoutView.as_view(), name='create'),
    path('detail/<int:pk>', views.HandoutDetailView.as_view(), name='detail'),
    path('update/<int:pk>', views.UpdateHandoutView.as_view(), name='update'),
    path('auth-control', views.AuthControlView.as_view(), name='auth-control'),
    path('invite', views.InviteView.as_view(), name='invite'),
    path('delete', views.delete, name='delete'),
    path('delete-handout', views.ConfirmDeleteView.as_view(), name='delete-handout'),
    path('close-success', views.after_close, name='close-success'),
    path('<uuid>', views.signin, name='signin'),
]
