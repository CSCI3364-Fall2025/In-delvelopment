from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('assessment/<int:assessment_id>/', views.view_assessment, name='view_assessment'),
    path('assessment/<int:assessment_id>/submit/', views.submit_assessment, name='submit_assessment'),
    path('published_results/', views.view_all_published_results, name='view_all_published_results'),
]
