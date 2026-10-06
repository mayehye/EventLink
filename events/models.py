from django.db import models
from accounts.models import Organizer, Customer  
import uuid 

class Category(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class Event(models.Model):
    organizer = models.ForeignKey('accounts.Organizer', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    STATUS_CHOICES = (
        ('Draft', 'Draft'),
        ('Published', 'Published'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Published')
    is_featured = models.BooleanField(default=False)
    
    title = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    is_free = models.BooleanField(default=False)
    gate_fee = models.CharField(max_length=100, blank=True, null=True)
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    image = models.ImageField(upload_to='event_posters/', blank=True, null=True)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    venue = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    description = models.TextField()

    @property
    def is_organizer_unverified(self):
        if self.organizer:
            return not self.organizer.is_verified
        return False

    def __str__(self):
        return self.title

class TicketTier(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ticket_tiers')
    name = models.CharField(max_length=100) # e.g., VIP, Regular, Odogu Seat
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_available = models.PositiveIntegerField()
    description = models.TextField(blank=True, null=True) # Perks description

    def __str__(self):
        return f"{self.event.title} - {self.name} (GH₵ {self.price})"

class Ticket(models.Model):
    ticket_id = models.CharField(max_length=50, unique=True, blank=True)
    order_reference = models.CharField(max_length=100, blank=True, null=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tickets')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='my_tickets', null=True, blank=True)
    tier = models.ForeignKey(TicketTier, on_delete=models.SET_NULL, null=True, blank=True) # Link ticket to tier
    guest_email = models.EmailField(blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    booking_date = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, default='Pending')
    
    # SCANNER TRACKING
    is_used = models.BooleanField(default=False)
    scanned_at = models.DateTimeField(null=True, blank=True)
    hidden_by_customer = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if not self.ticket_id:
            self.ticket_id = f"TKT-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        tier_name = self.tier.name if self.tier else "Standard"
        return f"{self.ticket_id} ({tier_name}) - {self.event.title}"

class EventAnnouncement(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='announcements')
    organizer = models.ForeignKey(Organizer, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.event.title}"