from django.contrib import admin
from .models import Course, Team, Assessment

# Register your models here.
admin.site.register(Course)
admin.site.register(Team)
admin.site.register(Assessment)
