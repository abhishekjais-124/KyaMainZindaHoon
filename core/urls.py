from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('link-partner/', views.link_partner, name='link_partner'),
    path('check-in/', views.check_in, name='check_in'),
    path('profile/', views.profile_view, name='profile'),
    path('invite_code_popup/', views.invite_code_popup, name='invite_code_popup'),
    path('get_invite_code/', views.get_invite_code, name='get_invite_code'),
    path('friends/', views.friends_view, name='friends'),
    path('loading/', views.loading_screen, name='loading_screen'),
    path('alert/danger', views.alert_danger, name='alert_danger'),
    path('alert/warning', views.alert_warning, name='alert_warning'),
]