from django.contrib import admin
from .models import Organizer, Customer

# Register your models here.
admin.site.register(Organizer)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    # This makes the admin list view cleaner by showing the username and phone
    list_display = ('user', 'phone_number')
    search_fields = ('user__username', 'phone_number')


from django.contrib import admin
from .models import Organizer, Customer, PayoutRequest

@admin.register(PayoutRequest)
class PayoutRequestAdmin(admin.ModelAdmin):
    list_display = ('organizer', 'amount', 'momo_number', 'momo_network', 'status', 'created_at')
    list_filter = ('status', 'momo_network', 'created_at')
    search_fields = ('organizer__organization_name', 'momo_number')
    actions = ['mark_as_paid']

    @admin.action(description='Mark selected payout requests as Paid')
    def mark_as_paid(self, request, queryset):
        queryset.update(status='Paid')
        self.message_user(request, "Selected payout requests have been marked as Paid.")