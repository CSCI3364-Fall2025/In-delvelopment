from django.urls import path
from assessments.views import send_deadline_notifications_view
from .views import student_average_score, professor_average_scores
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('assessment/<int:assessment_id>/', views.view_assessment, name='view_assessment'),
    path('assessment/<int:assessment_id>/save_progress/', views.save_progress, name='save_progress'),
    path('assessment/<int:assessment_id>/submit/', views.submit_assessment, name='submit_assessment'),
    path('assessment/<int:assessment_id>/comments/', views.view_comments, name='view_comments'),
    path('published_results/', views.view_all_published_results, name='view_all_published_results'),
    path('profile/<str:name>', views.edit_profile, name='edit_profile'),
    path('send-deadline-notifications/', send_deadline_notifications_view, name='send_deadline_notifications'),
    path('student-average/', student_average_score, name='student_average'),
    path('professor-average/', professor_average_scores, name='professor_average'),
    path('courses', views.course_dashboard, name='course_dashboard'),
    path('courses/create', views.create_course, name='create_course'),
    path('courses/<str:course_name>', views.view_course, name='view_course'),
    path('invite-students/', views.invite_students, name='invite_students'),
    path('debug-role/', views.debug_user_role, name='debug_role'),
    path('test-email/', views.test_email, name='test_email'),
    path('fix-session-role/', views.fix_session_role, name='fix_session_role'),
    path('set-profile-role/<str:role>/', views.set_profile_role, name='set_profile_role'),
    path('create_peer_assessments/', views.create_peer_assessments, name='create_peer_assessments'),
    path('<str:course_name>/add_teams', views.add_teams, name='add_teams'),
    path('assessment/<int:assessment_id>/publish/', views.publish_assessment_results, name='publish_assessment_results'),
    path('assessment/<int:assessment_id>/results/', views.view_published_results, name='view_published_results'),
    path('<str:course_name>/edit_team/<int:team_pk>', views.edit_team, name='edit_team'),
    path('<str:course_name>/delete_team/<int:team_pk>', views.delete_team, name="delete_team"),
]
