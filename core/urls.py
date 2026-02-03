from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('link-partner/', views.link_partner, name='link_partner'),
    path('check-in/', views.check_in, name='check_in'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('invite_code_popup/', views.invite_code_popup, name='invite_code_popup'),
    path('get_invite_code/', views.get_invite_code, name='get_invite_code'),
    path('friends/', views.friends_view, name='friends'),
    path('friends/save_emergency/', views.friends_save_emergency, name='friends_save_emergency'),
    path('loading/', views.loading_screen, name='loading_screen'),
    path('alert/danger', views.alert_danger, name='alert_danger'),
    path('alert/warning', views.alert_warning, name='alert_warning'),
    path('sos/trigger/', views.sos_trigger, name='sos_trigger'),
    path('sos/has_emergency_contacts/', views.sos_has_emergency_contacts, name='sos_has_emergency_contacts'),
    path('sos/list/', views.sos_list, name='sos_list'),
    path('sos/resolve/', views.sos_resolve, name='sos_resolve'),
    path('sos/resolved-notifications/', views.sos_resolved_notifications, name='sos_resolved_notifications'),
    path('sos/resolved-notifications/seen/', views.sos_resolved_notifications_seen, name='sos_resolved_notifications_seen'),
]