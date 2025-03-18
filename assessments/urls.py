from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('assessment/<int:assessment_id>/', views.view_assessment, name='view_assessment'),
    path('assessment/<int:assessment_id>/save_progress/', views.save_progress, name='save_progress'),
    path('assessment/<int:assessment_id>/submit/', views.submit_assessment, name='submit_assessment'),
    path('assessment/<int:assessment_id>/comments/', views.view_comments, name='view_comments'),
    path('published_results/', views.view_all_published_results, name='view_all_published_results'),
]
