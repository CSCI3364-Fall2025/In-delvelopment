from django.urls import path
from assessments.views import send_deadline_notifications_view
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
]
