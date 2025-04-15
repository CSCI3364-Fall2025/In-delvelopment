from celery import shared_task
from django.utils.timezone import now, timedelta
from assessments.models import Assessment

@shared_task
def peer_assessment_due_date_reminder():

    due_date = now() + timedelta(hours=24)

    assessments = Assessment.objects.filter(due_date=due_date)

    # for assessment in assessments:
    #     course = assessments.course
