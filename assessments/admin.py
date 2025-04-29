from django.contrib import admin
from .models import (
    Course, Team, Assessment, AssessmentSubmission,
    LikertQuestion, LikertResponse,
    OpenEndedQuestion, OpenEndedResponse
)

# Register simple models
admin.site.register(Course)
admin.site.register(Team)
admin.site.register(Assessment)

# Inlines for showing related data
class LikertResponseInline(admin.TabularInline):
    model = LikertResponse
    extra = 0
    readonly_fields = ['question', 'teammate', 'rating']
    can_delete = False

class OpenEndedResponseInline(admin.TabularInline):
    model = OpenEndedResponse
    extra = 0
    readonly_fields = ['question', 'teammate', 'response_text']
    can_delete = False

# Custom admin for AssessmentSubmission
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
        'custom_likert_responses',
        'custom_open_ended_responses',
        'feedback',
        'submitted_at'
    )
    list_display_links = ('id', 'assessment', 'student')
    search_fields = ('student', 'assessed_peer__username', 'assessment__title', 'feedback')
    list_filter = ('assessment', 'assessed_peer')
    
    inlines = [LikertResponseInline, OpenEndedResponseInline] 

    def custom_likert_responses(self, obj):
        responses = obj.likert_responses.all()
        return ", ".join(f"{r.rating}" for r in responses)
    custom_likert_responses.short_description = "Custom Likert Responses"

    def custom_open_ended_responses(self, obj):
        responses = obj.open_ended_responses.all()
        return ", ".join(f"{r.response_text[:15]}" for r in responses if r.response_text)
    custom_open_ended_responses.short_description = "Custom Open-Ended Responses"
