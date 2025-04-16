from django.contrib import admin
from .models import Course, Team, Assessment, AssessmentSubmission

# Register your models here.
admin.site.register(Course)
admin.site.register(Team)
admin.site.register(Assessment)

@admin.register(AssessmentSubmission)
class AssessmentSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'assessment',
        'student',
        'assessed_peer',
        'contribution',
        'teamwork',
        'communication',
        'feedback',
        'submitted_at'
    )
    list_display_links = ('id', 'assessment', 'student')  # optional
    search_fields = ('student', 'assessed_peer__username', 'assessment__title', 'feedback')
    list_filter = ('assessment', 'assessed_peer')
