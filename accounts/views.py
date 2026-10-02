from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Sum, Q
from django.contrib import messages
from .models import Organizer, Customer, PayoutRequest
from .forms import OrganizerProfileForm, PayoutSettingsForm
from events.models import Ticket
import requests

# 1. SMART LOGIN
def login_user(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            if hasattr(user, 'organizer_profile') or hasattr(user, 'organizer'):
                request.session['is_organizer'] = True
                return redirect('events:dashboard')
            else:
                request.session['is_organizer'] = False
                return redirect('events:home')
    else:
        form = AuthenticationForm()
        
    return render(request, 'accounts/login.html', {'form': form})

# 2. CUSTOMER REGISTRATION
def register_customer(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Customer.objects.create(user=user)
            login(request, user)
            request.session['is_organizer'] = False
            return redirect('events:home')
    else:
        form = UserCreationForm()
        
    return render(request, 'accounts/register_customer.html', {'form': form})

# 3. ORGANIZER REGISTRATION
def register_organizer(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        org_name = request.POST.get('organization_name')
        phone = request.POST.get('phone_number')
        
        if form.is_valid() and org_name and phone:
            user = form.save()
            Organizer.objects.create(
                user=user,
                organization_name=org_name,
                phone_number=phone,
                verification_status='Unverified'
            )
            login(request, user)
            request.session['is_organizer'] = True
            return redirect('events:dashboard')
    else:
        form = UserCreationForm()
        
    return render(request, 'accounts/register.html', {'form': form})

# 4. LOGOUT
def logout_user(request):
    logout(request)
    return redirect('events:home')


# ---------------- PAYOUT SETTINGS & WITHDRAWALS ----------------

@login_required(login_url='/accounts/login/')
def payout_settings(request):
    organizer = getattr(request.user, 'organizer', None) or getattr(request.user, 'organizer_profile', None)
    if not organizer:
        return redirect('events:home')

    # 1. Calculate Total Earned: Sum total_price of paid tickets sold by this organizer
    organizer_tickets = Ticket.objects.filter(
        event__organizer=organizer
    ).filter(
        Q(payment_status__iexact='Paid') | Q(payment_status__iexact='success')
    )
    
    gross_revenue = organizer_tickets.aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')
    
    # Platform commission (e.g., 10% platform fee, organizer keeps 90%)
    platform_commission_rate = Decimal('0.10')
    total_earned = gross_revenue * (Decimal('1.00') - platform_commission_rate)

    # 2. Fetch Payout Requests safely
    payouts = PayoutRequest.objects.filter(organizer=organizer)
    
    pending_amount = payouts.filter(status__iexact='Pending').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    paid_amount = payouts.filter(Q(status__iexact='Paid') | Q(status__iexact='Approved')).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # 3. Available Balance = Total Earned - (Paid Withdrawals + Pending Withdrawals)
    # This immediately deducts the balance upon clicking request withdrawal!
    available_balance = total_earned - (paid_amount + pending_amount)
    if available_balance < Decimal('0.00'):
        available_balance = Decimal('0.00')

    # 4. Handle Withdrawal Form Submission
    if request.method == 'POST':
        try:
            requested_amount = Decimal(request.POST.get('amount', '0'))
        except (ValueError, InvalidOperation):
            requested_amount = Decimal('0.00')

        if requested_amount <= Decimal('0.00'):
            messages.error(request, "Please enter a valid withdrawal amount.")
        elif requested_amount > available_balance:
            messages.error(request, f"Requested amount (GHS {requested_amount}) exceeds your available balance (GHS {available_balance}).")
        else:
            PayoutRequest.objects.create(
                organizer=organizer,
                amount=requested_amount,
                status='Pending'
            )
            messages.success(request, f"Successfully requested withdrawal of GHS {requested_amount:.2f}. Pending admin review.")
            return redirect('accounts:payout_settings')

    context = {
        'organizer': organizer,
        'total_earned': total_earned,
        'available_balance': available_balance,
        'pending_amount': pending_amount,
        'paid_amount': paid_amount,
    }
    return render(request, 'accounts/payout_settings.html', context)

@login_required(login_url='/accounts/login/')
def request_payout(request):
    """Alias view for request_payout, routing directly to payout settings."""
    return payout_settings(request)

from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.conf import settings
from .models import Organizer, PayoutRequest
from events.models import Ticket

@login_required(login_url='/accounts/login/')
def request_payout(request):
    organizer = getattr(request.user, 'organizer', None) or getattr(request.user, 'organizer_profile', None)
    if not organizer:
        return redirect('events:home')

    # Check if organizer has Momo details set up
    if not organizer.momo_number:
        messages.error(request, "Please set up your payout MoMo details first.")
        return redirect('accounts:payout_settings')

    # 1. Calculate Total Earned from paid tickets
    organizer_tickets = Ticket.objects.filter(
        event__organizer=organizer
    ).filter(
        Q(payment_status__iexact='Paid') | Q(payment_status__iexact='success')
    )
    gross_revenue = organizer_tickets.aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')
    
    platform_commission_rate = Decimal('0.10')
    total_earned = gross_revenue * (Decimal('1.00') - platform_commission_rate)

    # 2. Calculate Payout Requests (Pending + Paid)
    payouts = PayoutRequest.objects.filter(organizer=organizer)
    pending_amount = payouts.filter(status__iexact='Pending').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    paid_amount = payouts.filter(Q(status__iexact='Paid') | Q(status__iexact='Approved')).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # 3. Available Balance
    available_balance = total_earned - (paid_amount + pending_amount)
    if available_balance < Decimal('0.00'):
        available_balance = Decimal('0.00')

    # 4. Handle Withdrawal Submission
    if request.method == 'POST':
        try:
            requested_amount = Decimal(request.POST.get('amount', '0'))
        except (ValueError, InvalidOperation):
            requested_amount = Decimal('0.00')

        if requested_amount <= Decimal('0.00'):
            messages.error(request, "Enter a valid withdrawal amount.")
        elif requested_amount > available_balance:
            messages.error(request, f"Requested amount (GHS {requested_amount}) exceeds your available balance (GHS {available_balance}).")
        else:
            PayoutRequest.objects.create(
                organizer=organizer,
                amount=requested_amount,
                momo_number=organizer.momo_number,
                momo_network=organizer.momo_network,
                status='Pending'
            )
            messages.success(request, f"Withdrawal request of GHS {requested_amount:.2f} submitted successfully! Admin will send funds shortly.")
            return redirect('accounts:request_payout')

    context = {
        'organizer': organizer,
        'total_earned': total_earned,
        'available_balance': available_balance,
        'pending_amount': pending_amount,
        'paid_amount': paid_amount,
    }
    return render(request, 'accounts/request_payout.html', context)

# --- OLD PAYSTACK TRANSFER RECIPIENT API (Commented out) ---
        # name = request.POST.get('business_name') or organizer.organization_name
        # account_number = request.POST.get('account_number')
        # bank_code = request.POST.get('settlement_bank')
        # 
        # url = "https://api.paystack.co/transferrecipient"
        # headers = {
        #     "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        #     "Content-Type": "application/json",
        # }
        # payload = {
        #     "type": "mobile_money",
        #     "name": name,
        #     "account_number": account_number,
        #     "bank_code": bank_code,
        #     "currency": "GHS"
        # }
        # 
        # response = requests.post(url, headers=headers, json=payload)
        # res_data = response.json()
        # 
        # if res_data.get("status"):
        #     organizer.paystack_recipient_code = res_data["data"]["recipient_code"]
        #     organizer.save()
        #     messages.success(request, "Payout account saved successfully!")
        #     return redirect('accounts:payout_settings')
        # else:
        #     messages.error(request, f"Error: {res_data.get('message')}")



@login_required
def profile_settings(request):
    organizer = Organizer.objects.filter(user=request.user).first()
    customer = Customer.objects.filter(user=request.user).first()

    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name', request.user.first_name)
        request.user.last_name = request.POST.get('last_name', request.user.last_name)
        request.user.email = request.POST.get('email', request.user.email)
        request.user.save()

        phone = request.POST.get('phone_number')
        if organizer and phone:
            organizer.phone_number = phone
            organizer.save()

        messages.success(request, "Profile updated successfully!")
        return redirect('accounts:settings')

    return render(request, 'accounts/profile_settings.html', {
        'organizer': organizer,
        'customer': customer
    })