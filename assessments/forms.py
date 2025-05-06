from django import forms
from .models import Assessment, Course

class PeerAssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = ['title', 'description', 'course', 'open_date', 'due_date']
        widgets = {
            'open_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'course': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(PeerAssessmentForm, self).__init__(*args, **kwargs)
        
        if user:
            # Filter courses to only show those created by this professor
            self.fields['course'].queryset = Course.objects.filter(created_by=user)
