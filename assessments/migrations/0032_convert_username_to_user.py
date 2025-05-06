from django.db import migrations

def convert_username_to_user(apps, schema_editor):
    AssessmentSubmission = apps.get_model('assessments', 'AssessmentSubmission')
    User = apps.get_model('auth', 'User')
    
    # Get all submissions
    for submission in AssessmentSubmission.objects.all():
        try:
            # Try to find the user by username
            user = User.objects.get(username=submission.student)
            # Update the submission with the user object
            submission.student = user
            submission.save()
        except User.DoesNotExist:
            # If user doesn't exist, delete the submission or handle as needed
            submission.delete()

class Migration(migrations.Migration):
    dependencies = [
        ('assessments', '0030_alter_assessmentsubmission_unique_together'),
    ]

    operations = [
        migrations.RunPython(convert_username_to_user),
    ]
