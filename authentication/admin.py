from django.contrib import admin
from .models import UserProfile
from allauth.socialaccount.models import SocialApp

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__email', 'user__username')

admin.site.register(SocialApp)
