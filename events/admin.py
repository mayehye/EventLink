from django.contrib import admin
from .models import Category, Event, Ticket

# Simple registration for Category
admin.site.register(Category)

# We might as well register Event and Ticket so you can see them in the admin panel!
admin.site.register(Event)
admin.site.register(Ticket)