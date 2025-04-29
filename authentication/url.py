from django.urls import path
from . import views
from .views import verify_submission

app_name = 'authentication'

urlpatterns = [
    path('debug-oauth/', views.debug_oauth, name='debug_oauth'),
    path('debug-oauth-flow/', views.debug_oauth_flow, name='debug_oauth_flow'),
    path("verify-submission/", verify_submission, name="verify_submission"),
]
