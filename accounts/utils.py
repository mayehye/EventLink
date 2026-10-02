import requests
from django.conf import settings

def create_paystack_subaccount(organizer):
    url = "https://api.paystack.co/subaccount"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    
    # Map local network choices to Paystack bank codes or mobile money identifiers if needed
    # Note: Paystack Ghana mobile money integrations use specific bank codes (e.g., MTG for MTN, VOD for Vodafone, ATL for AirtelTigo)
    bank_code_map = {
        'mtn': 'MTN',
        'vodafone': 'VOD',
        'airteltigo': 'ATL',
    }
    
    data = {
        "business_name": organizer.organization_name,
        "settlement_bank": bank_code_map.get(organizer.momo_network, 'MTN'),
        "account_number": organizer.momo_number,
        "percentage_charge": 10.0, # Adjust your platform commission split percentage here
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        res_data = response.json()
        
        if res_data.get('status'):
            subaccount_code = res_data['data']['subaccount_code']
            organizer.paystack_subaccount_code = subaccount_code
            organizer.is_subaccount_active = True
            organizer.save()
            return True, "Subaccount connected successfully!"
        else:
            return False, res_data.get('message', 'Failed to connect subaccount with Paystack.')
    except Exception as e:
        return False, str(e)