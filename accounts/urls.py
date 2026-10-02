from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    # --- YOUR ORIGINAL PATHS ---
    path('register/', views.register_customer, name='register'),
    path('register/organizer/', views.register_organizer, name='register_organizer'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    
    # 1. General Profile Settings (Name, email, phone)
    path('settings/', views.profile_settings, name='settings'),

    # 2. Automated Paystack Payout Settings
    path('payout-settings/', views.payout_settings, name='payout_settings'),

    # --- NEW PASSWORD RESET FLOW ---
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset_form.html',
        email_template_name='accounts/password_reset_email.html',
        success_url='/accounts/password-reset/done/'
    ), name='password_reset'),
    
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url='/accounts/password-reset-complete/'
    ), name='password_reset_confirm'),
    
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
    path('request-payout/', views.request_payout, name='request_payout'), # <--- Add this line
]