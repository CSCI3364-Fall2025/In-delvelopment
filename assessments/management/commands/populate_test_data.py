from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from authentication.models import UserProfile
from assessments.models import (
    Course, Team, Assessment, LikertQuestion, OpenEndedQuestion, 
    AssessmentSubmission, LikertResponse, OpenEndedResponse, StudentScore
)
import random
from datetime import timedelta

class Command(BaseCommand):
    help = 'Populates the database with a sample course and assessment for testing'

    def add_arguments(self, parser):
        parser.add_argument('--current-user', type=str, help='Username of the current user to add to a team')

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating sample test data...')
        current_username = kwargs.get('current_user')
        
        # Create professor if not exists
        professor, created = User.objects.get_or_create(
            username='professor',
            email='professor@example.com',
            defaults={'first_name': 'Professor', 'last_name': 'Smith'}
        )
        if created:
            professor.set_password('password123')
            professor.save()
            UserProfile.objects.get_or_create(user=professor, defaults={'role': 'professor'})
            self.stdout.write(self.style.SUCCESS(f'Created professor: {professor.username}'))
        
        # Create a few sample students
        student_data = [
            ('jsmith', 'John', 'Smith', 'jsmith@example.com'),
            ('agarcia', 'Ana', 'Garcia', 'agarcia@example.com'),
            ('mwilliams', 'Michael', 'Williams', 'mwilliams@example.com'),
            ('jjohnson', 'Jennifer', 'Johnson', 'jjohnson@example.com'),
        ]
        
        students = []
        for username, first_name, last_name, email in student_data:
            student, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email
                }
            )
            if created:
                student.set_password('password123')
                student.save()
                UserProfile.objects.get_or_create(user=student, defaults={'role': 'student'})
                self.stdout.write(self.style.SUCCESS(f'Created student: {student.username}'))
            students.append(student)
        
        # Create a sample course
        sample_course, created = Course.objects.get_or_create(
            name="Introduction to Computer Science",
            course_code="CS101",
            semester="Fall",
            year=2023,
            defaults={
                'description': 'A sample course for testing the peer assessment system',
                'created_by': professor
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created course: {sample_course.course_code}'))
        
        # Add students to the course
        for student in students:
            sample_course.students.add(student)
        
        # Create multiple teams for the sample course
        team1, created = Team.objects.get_or_create(
            name='Sample Team 1',
            course=sample_course,
            defaults={'is_active': True}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created team: {team1.name}'))
        
        team2, created = Team.objects.get_or_create(
            name='Sample Team 2',
            course=sample_course,
            defaults={'is_active': True}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created team: {team2.name}'))
        
        # Add students to different teams
        team1.members.add(students[0])  # John Smith
        team1.members.add(students[1])  # Ana Garcia
        
        # Last two students in Team 2
        team2.members.add(students[2])  # Michael Williams
        team2.members.add(students[3])  # Jennifer Johnson
        
        # Add current user to Team 1 if specified
        current_user = None
        if current_username:
            try:
                current_user = User.objects.get(username=current_username)
                sample_course.students.add(current_user)
                team1.members.add(current_user)
                self.stdout.write(self.style.SUCCESS(f'Added current user {current_username} to {team1.name}'))
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Current user {current_username} not found'))
        
        # Create a sample assessment
        now = timezone.now()
        assessment, created = Assessment.objects.get_or_create(
            title='Sample Peer Assessment',
            course=sample_course,
            defaults={
                'description': 'A sample peer assessment for testing',
                'open_date': now - timedelta(days=7),
                'due_date': now + timedelta(days=7),
                'published': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created assessment: {assessment.title}'))
            
            # Add Likert questions
            likert_questions = [
                'This team member contributed equally to the project.',
                'This team member communicated effectively with the team.',
                'This team member completed their assigned tasks on time.',
                'I would want to work with this team member again in the future.'
            ]
            
            for i, question in enumerate(likert_questions):
                LikertQuestion.objects.create(
                    assessment=assessment,
                    question_text=question,
                    order=i,
                    question_type='team'
                )
                self.stdout.write(self.style.SUCCESS(f'Created Likert question {i+1}'))
            
            # Add open-ended questions
            open_ended_questions = [
                'What were this team member\'s strengths?',
                'What areas could this team member improve in?',
                'Additional comments about this team member\'s performance:'
            ]
            
            for i, question in enumerate(open_ended_questions):
                OpenEndedQuestion.objects.create(
                    assessment=assessment,
                    question_text=question,
                    order=i,
                    question_type='team'
                )
                self.stdout.write(self.style.SUCCESS(f'Created open-ended question {i+1}'))
        
        # Get all questions for the assessment
        likert_questions = LikertQuestion.objects.filter(assessment=assessment)
        open_ended_questions = OpenEndedQuestion.objects.filter(assessment=assessment)
        
        # Create submission for John Smith (evaluating Ana Garcia)
        john = students[0]  # John Smith
        ana = students[1]   # Ana Garcia
        
        # Check if the model has the right fields
        try:
            # Check if submission already exists
            existing_submission = AssessmentSubmission.objects.filter(
                assessment=assessment,
                student=john.username
            ).exists()
            
            if not existing_submission:
                john_submission = AssessmentSubmission.objects.create(
                    assessment=assessment,
                    student=john.username,
                    contribution=random.randint(3, 5),
                    teamwork=random.randint(3, 5),
                    communication=random.randint(3, 5),
                    feedback="Sample feedback from John about Ana's performance",
                    assessed_peer=ana
                )
                self.stdout.write(self.style.SUCCESS(f'Created submission for {john.first_name} evaluating {ana.first_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Submission for {john.first_name} already exists, skipping'))
            
            # Create submission for Michael Williams (evaluating Jennifer Johnson)
            michael = students[2]  # Michael Williams
            jennifer = students[3]  # Jennifer Johnson
            
            existing_submission = AssessmentSubmission.objects.filter(
                assessment=assessment,
                student=michael.username
            ).exists()
            
            if not existing_submission:
                michael_submission = AssessmentSubmission.objects.create(
                    assessment=assessment,
                    student=michael.username,
                    contribution=random.randint(2, 5),
                    teamwork=random.randint(2, 5),
                    communication=random.randint(2, 5),
                    feedback="Sample feedback from Michael about Jennifer's performance",
                    assessed_peer=jennifer
                )
                self.stdout.write(self.style.SUCCESS(f'Created submission for {michael.first_name} evaluating {jennifer.first_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Submission for {michael.first_name} already exists, skipping'))
            
            # NO LONGER CREATING SUBMISSION FOR CURRENT USER
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating submissions: {str(e)}'))
            self.stdout.write(self.style.WARNING('Skipping submission creation due to model incompatibility'))
        
        self.stdout.write(self.style.SUCCESS('Successfully populated test data with teams and submissions!'))
