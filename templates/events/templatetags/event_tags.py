from django import template
from events.models import Event

register = template.Library()

@register.simple_tag
def is_event_unverified(event_obj):
    """Safely returns True if the event has an organizer and that organizer is NOT verified."""
    if event_obj and hasattr(event_obj, 'organizer') and event_obj.organizer:
        return not event_obj.organizer.is_verified
    return False