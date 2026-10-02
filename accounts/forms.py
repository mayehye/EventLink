from django import forms
from .models import Organizer

class OrganizerProfileForm(forms.ModelForm):
    class Meta:
        model = Organizer
        fields = ['organization_name', 'phone_number']
        
        widgets = {
            'organization_name': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control form-control-lg', 
                'type': 'tel', 
                'inputmode': 'numeric',
                'oninput': "this.value = this.value.replace(/[^0-9]/g, '')", 
                'maxlength': '15'
            }),
        }

class PayoutSettingsForm(forms.ModelForm):
    class Meta:
        model = Organizer
        fields = ['momo_number', 'momo_network']
        widgets = {
            'momo_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 0241234567'}),
            'momo_network': forms.Select(attrs={'class': 'form-select'}),
        }