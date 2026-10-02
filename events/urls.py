from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # Customer / Public Views
    path('', views.home, name='home'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),
    path('organizer/<int:organizer_id>/', views.organizer_public_profile, name='organizer_profile'),
    path('ticket/delete/<str:ticket_id>/', views.delete_scanned_ticket, name='delete_ticket'),
    # Ticketing & Checkout
    path('event/<int:event_id>/checkout/', views.checkout, name='checkout'),
    path('verify-payment/<str:reference>/', views.verify_payment, name='verify_payment'),
    path('my-tickets/', views.my_tickets, name='my_tickets'),
    path('my-tickets/delete/<str:ticket_id>/', views.delete_ticket, name='delete_ticket'), # NEW
    # Organizer Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/manage/<int:event_id>/', views.manage_event, name='manage_event'),
    path('dashboard/scan/<int:event_id>/', views.scan_ticket, name='scan_ticket'),
    path('dashboard/manage/<int:event_id>/scanned/', views.scanned_tickets_list, name='scanned_tickets_list'), # NEW
    path('dashboard/manage/<int:event_id>/clear-scanned/', views.clear_scanned_tickets, name='clear_scanned_tickets'), # NEW
    path('dashboard/create/', views.create_event, name='create_event'),
    path('dashboard/edit/<int:event_id>/', views.edit_event, name='edit_event'),
    path('dashboard/delete/<int:event_id>/', views.delete_event, name='delete_event'),
    # Platform Fees
    path('dashboard/checkout/<int:event_id>/', views.organizer_checkout, name='organizer_checkout'),
    path('dashboard/verify-fee/<int:event_id>/<str:reference>/', views.verify_organizer_payment, name='verify_organizer_payment'),
    path('dashboard/payouts/', views.setup_payouts, name='setup_payouts'),
    path('organizer/payout-setup/', views.setup_paystack_subaccount, name='setup_subaccount'),
    path('verify-payment/<str:reference>/', views.verify_payment, name='verify_payment'),
    path('ticket/<int:ticket_id>/download/', views.download_ticket, name='download_ticket'),
    path('event/<int:event_id>/broadcast/', views.broadcast_message, name='broadcast_message'),
    path('event/<int:event_id>/announcements/', views.event_announcements, name='event_announcements'),
    path('event/<int:event_id>/export-csv/', views.export_attendees_csv, name='export_attendees_csv'),
]