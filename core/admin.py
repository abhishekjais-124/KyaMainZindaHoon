from django.contrib import admin

# Register your models here.
from .models import Profile, UserPartnerMappings, SOSAlert

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'get_partners_display', 'invite_code', 'last_check_in', 'alert_sent')
	search_fields = ('user__email', 'invite_code')
	list_filter = ('alert_sent',)

	def get_partners_display(self, obj):
		partners = obj.get_partners()
		return ', '.join(p.user.email for p in partners) if partners else 'None'
	get_partners_display.short_description = 'Partners'

@admin.register(UserPartnerMappings)
class UserPartnerMappingsAdmin(admin.ModelAdmin):
	list_display = ('user', 'partner', 'is_active', 'is_emergency')
	list_filter = ('is_active', 'is_emergency')


@admin.register(SOSAlert)
class SOSAlertAdmin(admin.ModelAdmin):
	list_display = ('id', 'from_user', 'to_user', 'status', 'created_at', 'resolved_at', 'resolved_by')
	list_filter = ('status',)
	readonly_fields = ('created_at', 'resolved_at')
