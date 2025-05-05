from django.contrib import admin
from .models import UserProfile, ReportedError

# Register your models here
admin.site.register(UserProfile)
admin.site.register(ReportedError)
