from django.db import models
from django.conf import settings
from django.contrib.auth.models import User

class Organizer(models.Model):
    VERIFICATION_CHOICES = (
        ('unverified', 'unverified'),
        ('Verified', 'Verified'),
        ('Rejected', 'Rejected'),
    )

    # 1. User Relation
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organizer_profile')
    
    # 2. Organizer Details
    organization_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=20)
    
    # 3. Payout Mobile Money Fields
    momo_number = models.CharField(max_length=15, blank=True, null=True)
    momo_network = models.CharField(max_length=50, blank=True, null=True, choices=[
        ('mtn', 'MTN Mobile Money'),
        ('vodafone', 'Telecel Cash'),
        ('airteltigo', 'AirtelTigo Money'),
    ])
    paystack_recipient_code = models.CharField(max_length=100, blank=True, null=True)
    
    # Legacy / Optional Subaccount fields
    paystack_subaccount_code = models.CharField(max_length=100, blank=True, null=True)
    is_subaccount_active = models.BooleanField(default=False)

    # 4. Admin Verification System
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_CHOICES, default='unverified')
    unverified = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.organization_name} ({self.verification_status})"


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Customer: {self.user.username}"


class PayoutRequest(models.Model):
    organizer = models.ForeignKey(Organizer, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    momo_number = models.CharField(max_length=15)
    momo_network = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default='Pending') # Pending, Paid
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.organizer.organization_name} - GHS {self.amount} ({self.status})"