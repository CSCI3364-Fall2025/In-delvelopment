"""URL configuration for PeerAssess project."""

from django.contrib import admin
from django.urls import path, include

from assessments import views as assessment_views
from authentication import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', assessment_views.home, name='home'),
    path('dashboard/', assessment_views.dashboard, name='dashboard'),
    path('login/', auth_views.login_view, name='login'),
    path('signup/', auth_views.signup_view, name='signup'),
    path('logout/', auth_views.logout_view, name='logout'),
    path('save_progress', auth_views.save_progress, name='save_progress'),
    path('load_progress', auth_views.load_progress, name='load_progress'),
    path('verify-submission/', auth_views.verify_submission, name='verify_submission'),
    path('login-error/', auth_views.login_error, name='login_error'),
    path('assessments/', include('assessments.urls')),
    path('debug/', include([
        path('auth/', auth_views.debug_auth, name='debug_auth'),
        path('test_login', auth_views.test_login, name='test_login'),
    ])),
    path('about/', assessment_views.about, name='about'),
    path('report-issue', auth_views.report_issue, name='report_issue'),
    path('test-email', assessment_views.test_email, name='test_email'),
    path('test_email', assessment_views.test_email),
]
