from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path('debug-oauth/', views.debug_oauth, name='debug_oauth'),
    path('debug-oauth-flow/', views.debug_oauth_flow, name='debug_oauth_flow'),
]
