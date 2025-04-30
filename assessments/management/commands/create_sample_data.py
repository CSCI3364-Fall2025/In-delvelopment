from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from authentication.models import UserProfile
from assessments.models import Course, Team, Assessment, LikertQuestion, OpenEndedQuestion, AssessmentSubmission, LikertResponse, OpenEndedResponse, StudentScore
import random
from datetime import timedelta

class Command(BaseCommand):
    help = 'Creates sample data for testing the peer assessment system'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating sample data...')
        
        # Create professor
        professor, created = User.objects.get_or_create(
            username='professor',
            email='professor@example.com',
            defaults={'first_name': 'Professor', 'last_name': 'Smith'}
        )
        if created:
            professor.set_password('password123')
            professor.save()
            # Check if profile exists before creating
            UserProfile.objects.get_or_create(user=professor, defaults={'role': 'professor'})
            self.stdout.write(self.style.SUCCESS(f'Created professor: {professor.username}'))
        
        # Create students
        students = []
        for i in range(1, 9):
            student, created = User.objects.get_or_create(
                username=f'student{i}',
                email=f'student{i}@example.com',
                defaults={'first_name': f'Student', 'last_name': f'{i}'}
            )
            if created:
                student.set_password('password123')
                student.save()
                # Check if profile exists before creating
                UserProfile.objects.get_or_create(user=student, defaults={'role': 'student'})
                self.stdout.write(self.style.SUCCESS(f'Created student: {student.username}'))
            students.append(student)
        
        # Create course
        course, created = Course.objects.get_or_create(
            name='CS101',
            defaults={
                'description': 'Introduction to Computer Science',
                'created_by': professor,
                'course_code': 'CS101',
                'year': '2025',
                'semester': 'Spring'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created course: {course.name}'))
        
        # Create teams
        team1, created = Team.objects.get_or_create(
            name='Team Alpha',
            course=course
        )
        if created:
            team1.members.add(students[0], students[1], students[2], students[3])
            self.stdout.write(self.style.SUCCESS(f'Created team: {team1.name}'))
        
        team2, created = Team.objects.get_or_create(
            name='Team Beta',
            course=course
        )
        if created:
            team2.members.add(students[4], students[5], students[6], students[7])
            self.stdout.write(self.style.SUCCESS(f'Created team: {team2.name}'))
        
        # Create assessment - FIXED VERSION
        now = timezone.now()
        assessment, created = Assessment.objects.get_or_create(
            title='Midterm Peer Review',
            defaults={
                'course': course,
                'open_date': now - timedelta(days=5),
                'due_date': now + timedelta(days=5),
                'is_published': True,
                'self_assessment_required': False
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created assessment: {assessment.title}'))
            
            # Create Likert questions
            likert_questions = [
                LikertQuestion.objects.create(
                    assessment=assessment,
                    question_text='How would you rate this team member\'s overall contribution to the project?',
                    question_type='individual',
                    order=1
                ),
                LikertQuestion.objects.create(
                    assessment=assessment,
                    question_text='How effectively did the team collaborate on this project?',
                    question_type='team',
                    order=2
                ),
                LikertQuestion.objects.create(
                    assessment=assessment,
                    question_text='How would you rate this team member\'s communication skills?',
                    question_type='individual',
                    order=3
                )
            ]
            
            # Create Open-ended questions
            open_ended_questions = [
                OpenEndedQuestion.objects.create(
                    assessment=assessment,
                    question_text='What specific contributions did this team member make to the project?',
                    question_type='individual',
                    order=1
                ),
                OpenEndedQuestion.objects.create(
                    assessment=assessment,
                    question_text='What are the team\'s strengths and areas for improvement?',
                    question_type='team',
                    order=2
                )
            ]
            
            # Create submissions for Team Alpha
            team1_members = list(team1.members.all())
            for submitter in team1_members:
                # Create only one submission per student per assessment
                submission, _ = AssessmentSubmission.objects.get_or_create(
                    assessment=assessment,
                    student=submitter.username,
                    defaults={
                        'contribution': random.randint(3, 5),
                        'teamwork': random.randint(3, 5),
                        'communication': random.randint(3, 5),
                        'feedback': f"This is feedback from {submitter.username} about the team's performance."
                    }
                )
                
                # Now create responses for each peer within this submission
                for peer in team1_members:
                    if submitter != peer:
                        # Create Likert responses for individual questions
                        for question in likert_questions:
                            if question.question_type == 'individual':
                                LikertResponse.objects.get_or_create(
                                    submission=submission,
                                    question=question,
                                    teammate=peer,
                                    defaults={'rating': random.randint(3, 5)}
                                )
                        
                        # Create Open-ended responses for individual questions
                        for question in open_ended_questions:
                            if question.question_type == 'individual':
                                OpenEndedResponse.objects.get_or_create(
                                    submission=submission,
                                    question=question,
                                    teammate=peer,
                                    defaults={'response_text': f"This is a detailed response about {peer.username}'s specific contributions."}
                                )
                
                # Create team-level responses (only once per submission)
                for question in likert_questions:
                    if question.question_type == 'team':
                        LikertResponse.objects.get_or_create(
                            submission=submission,
                            question=question,
                            defaults={'rating': random.randint(3, 5)}
                        )
                
                for question in open_ended_questions:
                    if question.question_type == 'team':
                        OpenEndedResponse.objects.get_or_create(
                            submission=submission,
                            question=question,
                            defaults={'response_text': "The team worked well together but could improve communication."}
                        )
            
            # Create professor scores for some students
            for student in team1_members[:2]:
                StudentScore.objects.get_or_create(
                    student=student,
                    assessment=assessment,
                    defaults={'score': random.uniform(7.0, 9.5)}
                )
        
        self.stdout.write(self.style.SUCCESS('Sample data creation complete!'))
        self.stdout.write(self.style.SUCCESS('Login credentials:'))
        self.stdout.write(self.style.SUCCESS('Professor: username=professor, password=password123'))
        self.stdout.write(self.style.SUCCESS('Students: username=student1-8, password=password123')) 