from django.contrib import admin

# Register your models here.
from .models import Profile, UserPartnerMappings

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'get_partner_email', 'invite_code', 'last_check_in', 'alert_sent')
	search_fields = ('user__email', 'invite_code')
	list_filter = ('alert_sent',)

	def get_partner_email(self, obj):
		partner = obj.get_partner()
		return partner.user.email if partner else 'None'
	get_partner_email.short_description = 'Partner'

@admin.register(UserPartnerMappings)
class UserPartnerMappingsAdmin(admin.ModelAdmin):
	list_display = ('user', 'partner', 'is_active')
	list_filter = ('is_active',)
