from django import forms
from .models import Event
from django.core.exceptions import ValidationError

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'category', 'is_free', 'gate_fee', 'ticket_price', 'image', 'date', 'start_time', 'end_time', 'venue', 'location', 'description']
        
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'e.g. Summer Beach Party'}),
            'category': forms.Select(attrs={'class': 'form-select form-control-lg'}),
            'is_free': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'width: 25px; height: 25px;'}),
            'gate_fee': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'e.g. Regular GH₵ 50, VIP GH₵ 100'}),
            'ticket_price': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': '0.00', 'step': '0.01'}),
            'image': forms.FileInput(attrs={'class': 'form-control form-control-lg'}),
            'date': forms.DateInput(attrs={'class': 'form-control form-control-lg', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control form-control-lg', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control form-control-lg', 'type': 'time'}),
            'venue': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'e.g. Accra Sports Stadium'}),
            'location': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'e.g. Accra, Ghana'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Tell attendees what to expect...'}),
        }

    # NEW: Smart Validation Logic
    def clean(self):
        cleaned_data = super().clean()
        is_free = cleaned_data.get('is_free')
        ticket_price = cleaned_data.get('ticket_price')

        if not is_free:
            # If it's a paid event, the price MUST be greater than 0
            if ticket_price is None or ticket_price <= 0:
                self.add_error('ticket_price', "Paid events must have a ticket price greater than 0.00.")
        else:
            # If they checked 'is_free', force the price to 0 in the database just to be safe
            cleaned_data['ticket_price'] = 0.00

        return cleaned_data
def clean(self):
        cleaned_data = super().clean()
        title = cleaned_data.get('title')
        date = cleaned_data.get('date')
        location = cleaned_data.get('location')

        if title and date and location:
            # Check for duplicates, but EXCLUDE the current event if we are editing it!
            duplicate_qs = Event.objects.filter(
                title__iexact=title, 
                date=date, 
                location__iexact=location
            )
            
            if self.instance and self.instance.pk:
                duplicate_qs = duplicate_qs.exclude(pk=self.instance.pk)
            
            if duplicate_qs.exists():
                raise ValidationError(
                    "An event with this title, date, and location is already listed by another organizer. "
                    "Please contact an administrator for verification before publishing."
                )
        return cleaned_data