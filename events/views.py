from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
import requests
import time
import uuid

from accounts.models import Customer, Organizer
from .forms import EventForm
from .models import Category, Event, EventAnnouncement, Ticket, TicketTier


# ---------------- PUBLIC VIEWS ----------------
def home(request):
  query = request.GET.get('q', '')
  category_id = request.GET.get('category', '')

  now = timezone.now()
  today = now.date()

  # 1. PROMOTIONAL SECTION: Promoted events from tomorrow onwards (not today)
  # FIX: Added status='Published'
  featured_verified_events = (
      Event.objects.filter(status='Published', is_featured=True, date__gt=today)
      .filter(
          Q(organizer__verification_status='Verified')
          | Q(organizer__is_verified=True)
      )
      .order_by('date')
  )

  if category_id:
    featured_verified_events = featured_verified_events.filter(
        category_id=category_id
    )

  # 2. LIVE SECTION: All events happening today (promoted or non-promoted)
  # FIX: Added status='Published'
  todays_events = Event.objects.filter(status='Published', date=today).order_by('start_time')

  if category_id:
    todays_events = todays_events.filter(category_id=category_id)

  # 3. UPCOMING GENERAL: All events (promoted & non-promoted) from tomorrow onwards
  # FIX: Added status='Published'
  events = Event.objects.filter(status='Published', date__gt=today).order_by('date', 'start_time')

  if query:
    events = events.filter(
        Q(title__icontains=query)
        | Q(location__icontains=query)
        | Q(description__icontains=query)
    )

  if category_id:
    events = events.filter(category_id=category_id)

  categories = Category.objects.all()

  context = {
      'events': events,
      'todays_events': todays_events,
      'featured_verified_events': featured_verified_events,
      'categories': categories,
      'search_query': query,
      'selected_category': category_id,
  }
  return render(request, 'events/home.html', context)


def event_detail(request, event_id):
  event = get_object_or_404(Event, id=event_id)
  context = {
      'event': event,
  }
  return render(request, 'events/event_detail.html', context)


def organizer_public_profile(request, organizer_id):
  organizer = get_object_or_404(Organizer, id=organizer_id)
  today = timezone.now().date()
  events = Event.objects.filter(
      organizer=organizer, status='Published', date__gte=today
  ).order_by('date')
  return render(
      request,
      'events/organizer_profile.html',
      {'organizer': organizer, 'events': events},
  )


# ---------------- CHECKOUT & PAYMENTS ----------------


@login_required
def checkout(request, event_id):
  event = get_object_or_404(Event, id=event_id)
  ticket_tiers = event.ticket_tiers.all()

  if request.method == 'POST':
    tier_id = request.POST.get('tier_id')
    quantity = int(request.POST.get('quantity', 1))

    tier = None
    if tier_id:
      tier = get_object_or_404(TicketTier, id=tier_id, event=event)
      if quantity > tier.quantity_available:
        messages.error(
            request,
            f'Sorry, only {tier.quantity_available} tickets left for'
            f' {tier.name}.',
        )
        return redirect('events:checkout', event_id=event.id)
      unit_price = tier.price
    else:
      unit_price = event.ticket_price or Decimal('0.00')

    total_amount = unit_price * quantity
    amount_in_pesewas = int(total_amount * 100)

    customer_profile, created = Customer.objects.get_or_create(user=request.user)
    customer_email = (
        request.user.email
        if (request.user.email and request.user.email.strip())
        else 'customer@eventlink.com'
    )
    order_reference = str(uuid.uuid4())

    for _ in range(quantity):
      Ticket.objects.create(
          event=event,
          customer=customer_profile,
          tier=tier,
          guest_email=customer_email,
          total_price=unit_price,
          order_reference=order_reference,
          payment_status='Pending',
      )

    organizer = event.organizer
    subaccount_code = getattr(organizer, 'paystack_subaccount_code', None)

    url = 'https://api.paystack.co/transaction/initialize'
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }

    data = {
        'email': customer_email,
        'amount': amount_in_pesewas,
        'reference': order_reference,
        'callback_url': request.build_absolute_uri(
            reverse('events:verify_payment', args=[order_reference])
        ),
    }

    if subaccount_code:
      data['subaccount'] = subaccount_code
      data['transaction_charge'] = int(amount_in_pesewas * 0.05)
      data['bearer'] = 'subaccount'

    try:
      response = requests.post(url, headers=headers, json=data, timeout=15)
      res_data = response.json()

      print('PAYSTACK DEBUG RESPONSE:', res_data)

      if res_data.get('status'):
        return redirect(res_data['data']['authorization_url'])
      else:
        err_msg = res_data.get('message', 'Initialization failed')
        messages.error(request, f'Paystack Error: {err_msg}')
        return redirect('events:checkout', event_id=event.id)
    except Exception as e:
      print('PAYSTACK EXCEPTION ERROR:', e)
      messages.error(request, f'Could not connect to payment gateway: {e}')
      return redirect('events:checkout', event_id=event.id)

  return render(
      request,
      'events/checkout.html',
      {'event': event, 'ticket_tiers': ticket_tiers},
  )


def verify_payment(request, reference):
  tickets = Ticket.objects.filter(order_reference=reference)
  if not tickets.exists():
    return redirect('events:home')

  first_ticket = tickets.first()

  if first_ticket.payment_status == 'Paid':
    return render(
        request,
        'events/ticket_success.html',
        {
            'event': first_ticket.event,
            'tickets': tickets,
            'total_paid': sum(t.total_price for t in tickets),
        },
    )

  url = f'https://api.paystack.co/transaction/verify/{reference}'
  headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}

  try:
    response = requests.get(url, headers=headers, timeout=10)
    response_data = response.json()
  except:
    tickets.update(payment_status='Failed')
    return render(request, 'events/ticket_success.html', {'failed': True})

  if (
      response_data.get('status')
      and response_data['data']['status'] == 'success'
  ):
    tickets.update(payment_status='Paid')

    try:
      recipient = (
          first_ticket.guest_email
          if first_ticket.guest_email
          else first_ticket.customer.user.email
      )
      html_message = render_to_string(
          'events/emails/ticket_receipt.html',
          {'event': first_ticket.event, 'tickets': tickets},
      )
      plain_message = strip_tags(html_message)

      send_mail(
          subject=f'Your Tickets: {first_ticket.event.title}',
          message=plain_message,
          from_email=settings.DEFAULT_FROM_EMAIL,
          recipient_list=[recipient],
          html_message=html_message,
          fail_silently=True,
      )
    except Exception as e:
      print(f'DEBUG: Failed to send email: {e}')

    return render(
        request,
        'events/ticket_success.html',
        {
            'event': first_ticket.event,
            'tickets': tickets,
            'total_paid': response_data['data']['amount'] / 100,
        },
    )
  else:
    tickets.update(payment_status='Failed')
    return render(request, 'events/ticket_success.html', {'failed': True})


@login_required(login_url='/accounts/login/')
def my_tickets(request):
  if hasattr(request.user, 'customer_profile'):
    tickets = Ticket.objects.filter(
        customer=request.user.customer_profile, payment_status='Paid'
    ).order_by('-booking_date')
  else:
    tickets = []
  return render(request, 'events/my_tickets.html', {'tickets': tickets})


@login_required(login_url='/accounts/login/')
def delete_ticket(request, ticket_id):
  if hasattr(request.user, 'customer_profile'):
    Ticket.objects.filter(
        ticket_id=ticket_id, customer=request.user.customer_profile
    ).delete()
  return redirect('events:my_tickets')


# ---------------- ORGANIZER DASHBOARD & EVENTS ----------------


@login_required(login_url='/accounts/login/')
def dashboard(request):
  organizer = getattr(request.user, 'organizer', None) or getattr(
      request.user, 'organizer_profile', None
  )
  if not organizer:
    return redirect('events:home')

  events = Event.objects.filter(organizer=organizer).order_by('-created_at')

  organizer_tickets = Ticket.objects.filter(
      event__in=events, payment_status='Paid'
  )
  total_tickets_sold = organizer_tickets.count()

  gross_revenue = (
      organizer_tickets.aggregate(total=Sum('total_price'))['total']
      or Decimal('0.00')
  )
  platform_commission_rate = Decimal('0.10')
  platform_fee = gross_revenue * platform_commission_rate
  organizer_net_share = gross_revenue - platform_fee
  context = {
      'events': events,
      'organizer': organizer,
      'is_verified': organizer.is_verified,
      'total_tickets_sold': total_tickets_sold,
      'gross_revenue': gross_revenue,
      'organizer_net_share': organizer_net_share,
      'platform_fee': platform_fee,
      'is_organizer_unverified': False,
  }
  return render(request, 'events/dashboard.html', context)


@login_required(login_url='/accounts/login/')
def create_event(request):
  organizer = getattr(request.user, 'organizer', None) or getattr(
      request.user, 'organizer_profile', None
  )
  if not organizer:
    messages.error(
        request, 'You must be a registered organizer to create events.'
    )
    return redirect('accounts:organizer_register')

  if request.method == 'POST':
    form = EventForm(request.POST, request.FILES)
    if form.is_valid():
      event = form.save(commit=False)
      event.organizer = organizer
      # Save the event first so it has a primary key (ID) assigned in the database
      event.save()

      # Save optional dynamic ticket tiers / tables only if names are provided
      tier_names = request.POST.getlist('tier_name[]')
      tier_prices = request.POST.getlist('tier_price[]')
      quantities = request.POST.getlist('tier_quantity[]')
      descriptions = request.POST.getlist('tier_description[]')

      has_valid_tier = False
      for i in range(len(tier_names)):
        name = tier_names[i].strip() if i < len(tier_names) else ''
        if name:
          has_valid_tier = True
          price_val = (
              Decimal(tier_prices[i].strip())
              if (i < len(tier_prices) and tier_prices[i].strip())
              else Decimal('0.00')
          )
          TicketTier.objects.create(
              event=event,
              name=name,
              price=price_val,
              quantity_available=(
                  quantities[i]
                  if (i < len(quantities) and quantities[i].strip())
                  else 100
              ),
              description=(
                  descriptions[i] if i < len(descriptions) else ''
              ),
          )
          if i == 0:
            event.ticket_price = price_val

      if not has_valid_tier:
        # FIX: form.cleaned_data is a dictionary, use .get() not getattr()
        form_price = form.cleaned_data.get('ticket_price')
        event.ticket_price = form_price if form_price is not None else Decimal('0.00')

      event.save()

      # Strict evaluation: is it free?
      # We demand payment ONLY IF the event is marked 'is_free' OR the base ticket price is 0 
      # (and there are no ticket tiers with a price > 0).
      is_free_event = False
      
      # 1. Check form clean data or model instance attribute for is_free flag
      if getattr(event, 'is_free', False) or form.cleaned_data.get('is_free', False):
        is_free_event = True
      # 2. Check if the base ticket price is less than 1 AND verify there are no custom ticket tiers priced 1 or above
      else:
        base_price_is_free = event.ticket_price is None or event.ticket_price < Decimal('1.00')
        has_paid_tiers = event.ticket_tiers.filter(price__gte=Decimal('1.00')).exists()
        
        if base_price_is_free and not has_paid_tiers:
            is_free_event = True

      # Grab the FREE_EVENT_PUBLISH_FEE from settings (default to 0.00 if missing or invalid)
      try:
          publish_fee = Decimal(str(getattr(settings, 'FREE_EVENT_PUBLISH_FEE', '0.00')))
      except:
          publish_fee = Decimal('0.00')

      # Demand payment ONLY if it's a free event AND the publication fee is strictly > 0
      if is_free_event and publish_fee > Decimal('0.00'):
        event.status = 'Draft'
        event.save()
        messages.info(
            request,
            f"Free event '{event.title}' created as Draft. Please complete the"
            ' publication fee payment to publish it.',
        )
        return redirect('events:organizer_checkout', event_id=event.id)
      else:
        # Otherwise (paid event OR free event with 0 fee), publish immediately
        event.status = 'Published'
        event.save()
        event_type_msg = "Free" if is_free_event else "Paid"
        messages.success(
            request,
            f"{event_type_msg} event '{event.title}' created and published successfully!",
        )
        return redirect('events:manage_event', event_id=event.id)
  else:
    form = EventForm()

  return render(request, 'events/create_event.html', {'form': form})


@login_required(login_url='/accounts/login/')
def edit_event(request, event_id):
  organizer = getattr(request.user, 'organizer', None) or getattr(
      request.user, 'organizer_profile', None
  )
  event = get_object_or_404(Event, id=event_id, organizer=organizer)

  if request.method == 'POST':
    form = EventForm(request.POST, request.FILES, instance=event)
    if form.is_valid():
      event = form.save()

      # Handle optional Ticket Tiers / Tables
      tier_ids = request.POST.getlist('tier_id[]')
      tier_names = request.POST.getlist('tier_name[]')
      tier_prices = request.POST.getlist('tier_price[]')
      quantities = request.POST.getlist('tier_quantity[]')
      descriptions = request.POST.getlist('tier_description[]')

      for i in range(len(tier_names)):
        name = tier_names[i].strip() if i < len(tier_names) else ''
        if not name:
          continue

        price = (
            Decimal(tier_prices[i].strip())
            if (i < len(tier_prices) and tier_prices[i].strip())
            else Decimal('0.00')
        )
        qty = (
            quantities[i]
            if (i < len(quantities) and quantities[i].strip())
            else 100
        )
        desc = descriptions[i] if i < len(descriptions) else ''

        if i < len(tier_ids) and tier_ids[i]:
          try:
            tier = TicketTier.objects.get(id=tier_ids[i], event=event)
            tier.name = name
            tier.price = price
            tier.quantity_available = qty
            tier.description = desc
            tier.save()
          except TicketTier.DoesNotExist:
            pass
        else:
          TicketTier.objects.create(
              event=event,
              name=name,
              price=price,
              quantity_available=qty,
              description=desc,
          )

      messages.success(request, 'Event and ticket tiers updated successfully!')
      return redirect('events:manage_event', event_id=event.id)
  else:
    form = EventForm(instance=event)

  return render(
      request, 'events/edit_event.html', {'form': form, 'event': event}
  )


@login_required(login_url='/accounts/login/')
def delete_event(request, event_id):
  organizer = getattr(request.user, 'organizer', None) or getattr(
      request.user, 'organizer_profile', None
  )
  event = get_object_or_404(Event, id=event_id, organizer=organizer)
  event.delete()
  messages.success(request, 'Event deleted.')
  return redirect('events:dashboard')


@login_required(login_url='/accounts/login/')
def manage_event(request, event_id):
  organizer = getattr(request.user, 'organizer', None) or getattr(
      request.user, 'organizer_profile', None
  )
  event = get_object_or_404(Event, id=event_id, organizer=organizer)

  tickets = Ticket.objects.filter(event=event, payment_status='Paid')
  total_sold = tickets.count()
  total_scanned = tickets.filter(is_used=True).count()
  revenue = sum(t.total_price for t in tickets)

  return render(
      request,
      'events/manage_event.html',
      {
          'event': event,
          'total_sold': total_sold,
          'total_scanned': total_scanned,
          'revenue': revenue,
      },
  )


# ---------------- QR SCANNER LOGIC ----------------


@login_required(login_url='/accounts/login/')
def scan_ticket(request, event_id):
  organizer = getattr(request.user, 'organizer', None) or getattr(
      request.user, 'organizer_profile', None
  )
  event = get_object_or_404(Event, id=event_id, organizer=organizer)

  message = None
  status = None

  if request.method == 'POST':
    ticket_id = request.POST.get('ticket_id', '').strip()

    try:
      ticket = Ticket.objects.get(ticket_id=ticket_id, event=event)
      tier_name = ticket.tier.name if ticket.tier else 'Standard'

      if ticket.payment_status != 'Paid':
        message = 'WARNING: This ticket has not been paid for!'
        status = 'warning'
      elif ticket.is_used:
        scanned_time = (
            ticket.scanned_at.strftime('%I:%M %p')
            if ticket.scanned_at
            else 'previously'
        )
        message = (
            'ALREADY SCANNED: This ticket was already checked in at'
            f' {scanned_time}.'
        )
        status = 'warning'
      else:
        ticket.is_used = True
        ticket.scanned_at = timezone.now()
        ticket.save()

        if ticket.customer:
          attendee = ticket.customer.user.username
        else:
          attendee = ticket.guest_email if ticket.guest_email else 'Guest'

        message = f'SUCCESS! [{tier_name.upper()}] - {attendee} checked in.'
        status = 'success'

    except Ticket.DoesNotExist:
      message = 'INVALID TICKET: This code does not exist for this event.'
      status = 'danger'

  # Calculate financial and scan statistics for paid tickets
  paid_tickets = Ticket.objects.filter(event=event, payment_status='Paid')
  total_sold_amount = (
      paid_tickets.aggregate(total=Sum('total_price'))['total'] or 0
  )
  total_scanned = paid_tickets.filter(is_used=True).count()

  context = {
      'event': event,
      'message': message,
      'status': status,
      'total_sold_amount': total_sold_amount,
      'total_scanned': total_scanned,
      'announcements': event.announcements.all().order_by('-created_at'),
  }
  return render(request, 'events/scan_ticket.html', context)


@login_required(login_url='/accounts/login/')
def scanned_tickets_list(request, event_id):
  organizer = getattr(request.user, 'organizer', None) or getattr(
      request.user, 'organizer_profile', None
  )
  event = get_object_or_404(Event, id=event_id, organizer=organizer)
  scanned_tickets = Ticket.objects.filter(event=event, is_used=True).order_by(
      '-scanned_at'
  )
  return render(
      request,
      'events/scanned_tickets_list.html',
      {'event': event, 'scanned_tickets': scanned_tickets},
  )


@login_required(login_url='/accounts/login/')
def clear_scanned_tickets(request, event_id):
  organizer = getattr(request.user, 'organizer', None) or getattr(
      request.user, 'organizer_profile', None
  )
  event = get_object_or_404(Event, id=event_id, organizer=organizer)
  Ticket.objects.filter(event=event, is_used=True).delete()
  return redirect('events:manage_event', event_id=event.id)


@login_required(login_url='/accounts/login/')
def delete_scanned_ticket(request, ticket_id):
  ticket = get_object_or_404(
      Ticket,
      ticket_id=ticket_id,
      event__tickets__customer=request.user.customer_profile,
      is_used=True,
  )
  ticket.delete()
  messages.success(request, 'Scanned ticket removed from your history.')
  return redirect('events:my_tickets')


import base64
from io import BytesIO
import qrcode


@login_required
def download_ticket(request, ticket_id):
  ticket = get_object_or_404(Ticket, id=ticket_id)
  user = request.user
  is_owner = False

  if hasattr(ticket, 'customer') and ticket.customer:
    if ticket.customer == user or getattr(ticket.customer, 'user', None) == user:
      is_owner = True
  if hasattr(ticket, 'user') and ticket.user == user:
    is_owner = True

  is_organizer = False
  if hasattr(ticket.event, 'organizer'):
    if ticket.event.organizer.user == user or ticket.event.organizer == getattr(
        user, 'organizer', None
    ):
      is_organizer = True

  if not (is_owner or is_organizer or user.is_superuser):
    from django.core.exceptions import PermissionDenied

    raise PermissionDenied('You do not have permission to view this ticket.')

  # --- GENERATE REAL QR CODE IN MEMORY ---
  qr_data = str(
      ticket.ticket_id if hasattr(ticket, 'ticket_id') else ticket.order_reference
  )

  qr = qrcode.QRCode(version=1, box_size=10, border=2)
  qr.add_data(qr_data)
  qr.make(fit=True)

  img = qr.make_image(fill_color='black', back_color='white')
  buffer = BytesIO()
  img.save(buffer, format='PNG')
  qr_base64 = base64.b64encode(buffer.getvalue()).decode()

  context = {
      'ticket': ticket,
      'event': ticket.event,
      'qr_base64': qr_base64,
  }
  return render(request, 'events/ticket_download.html', context)


# ---------------- PAYOUT STUBS & CHECKOUT ----------------


@login_required(login_url='/accounts/login/')
def setup_payouts(request):
  return redirect('accounts:payout_settings')


@login_required(login_url='/accounts/login/')
def organizer_checkout(request, event_id):
  """Initializes a Paystack transaction for a free event's publication fee

  using settings.FREE_EVENT_PUBLISH_FEE.
  """
  organizer = getattr(request.user, 'organizer', None) or getattr(
      request.user, 'organizer_profile', None
  )
  event = get_object_or_404(Event, id=event_id, organizer=organizer)

  # Pull free event publication fee safely from settings.py
  try:
      publication_fee = Decimal(str(getattr(settings, 'FREE_EVENT_PUBLISH_FEE', '0.00')))
  except:
      publication_fee = Decimal('0.00')

  # If the fee is 0, auto-publish and skip Paystack
  if publication_fee <= Decimal('0.00'):
      event.status = 'Published'
      event.save()
      messages.success(request, f"Free event '{event.title}' is now automatically published.")
      return redirect('events:manage_event', event_id=event.id)

  amount_in_pesewas = int(publication_fee * 100)

  order_reference = f'PUB-{uuid.uuid4()}'
  organizer_email = (
      request.user.email
      if (request.user.email and request.user.email.strip())
      else 'organizer@eventlink.com'
  )

  url = 'https://api.paystack.co/transaction/initialize'
  headers = {
      'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
      'Content-Type': 'application/json',
  }

  data = {
      'email': organizer_email,
      'amount': amount_in_pesewas,
      'reference': order_reference,
      'callback_url': request.build_absolute_uri(
          reverse('events:verify_organizer_payment', args=[event.id, order_reference])
      ),
      'metadata': {'event_id': event.id, 'type': 'event_publication'},
  }

  try:
    response = requests.post(url, headers=headers, json=data, timeout=15)
    res_data = response.json()
    print('PAYSTACK ORGANIZER DEBUG RESPONSE:', res_data)

    if res_data.get('status'):
      return redirect(res_data['data']['authorization_url'])
    else:
      err_msg = res_data.get('message', 'Initialization failed')
      messages.error(request, f'Paystack Error: {err_msg}')
      return redirect('events:manage_event', event_id=event.id)
  except Exception as e:
    print('PAYSTACK ORGANIZER EXCEPTION ERROR:', e)
    messages.error(request, f'Could not connect to payment gateway: {e}')
    return redirect('events:manage_event', event_id=event.id)


@login_required(login_url='/accounts/login/')
def verify_organizer_payment(request, event_id, reference):
  """Verifies the organizer's publication payment from Paystack.

  If successful, automatically publishes the event and redirects to manage
  event.
  """
  organizer = getattr(request.user, 'organizer', None) or getattr(
      request.user, 'organizer_profile', None
  )
  event = get_object_or_404(Event, id=event_id, organizer=organizer)

  url = f'https://api.paystack.co/transaction/verify/{reference}'
  headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}

  try:
    response = requests.get(url, headers=headers, timeout=10)
    response_data = response.json()
  except Exception as e:
    print('VERIFY EXCEPTION:', e)
    messages.error(request, 'Payment verification connection error.')
    return redirect('events:manage_event', event_id=event.id)

  if (
      response_data.get('status')
      and response_data['data']['status'] == 'success'
  ):
    # Automatically publish the event once payment is verified successfully
    event.status = 'Published'
    event.save()
    messages.success(
        request,
        f"Payment successful! Free event '{event.title}' is now automatically"
        ' published.',
    )
  else:
    messages.error(
        request,
        'Payment verification failed or was canceled. Event remains as Draft.',
    )

  return redirect('events:manage_event', event_id=event.id)


@login_required(login_url='/accounts/login/')
def setup_paystack_subaccount(request):
  return redirect('accounts:payout_settings')


def event_announcements(request, event_id):
  event = get_object_or_404(Event, id=event_id)
  announcements = event.announcements.all().order_by('-created_at')
  return render(
      request,
      'events/announcements_list.html',
      {'event': event, 'announcements': announcements},
  )


@login_required(login_url='/accounts/login/')
def broadcast_message(request, event_id):
  organizer = getattr(request.user, 'organizer', None) or getattr(
      request.user, 'organizer_profile', None
  )
  event = get_object_or_404(Event, id=event_id, organizer=organizer)

  if request.method == 'POST':
    announcement_msg = request.POST.get('message', '').strip()

    if announcement_msg:
      default_title = f'Update regarding {event.title}'
      EventAnnouncement.objects.create(
          event=event,
          organizer=event.organizer,
          title=default_title,
          message=announcement_msg,
      )
      messages.success(
          request,
          f'Announcement successfully broadcasted to all ticket holders for'
          f' {event.title}!',
      )
      return redirect('events:broadcast_message', event_id=event.id)
    else:
      messages.error(request, 'Please enter a message before broadcasting.')

  context = {
      'event': event,
      'announcements': event.announcements.all().order_by('-created_at'),
  }
  return render(request, 'events/broadcast_message.html', context)


import csv
from django.http import HttpResponse


@login_required(login_url='/accounts/login/')
def export_attendees_csv(request, event_id):
  organizer = getattr(request.user, 'organizer', None) or getattr(
      request.user, 'organizer_profile', None
  )
  event = get_object_or_404(Event, id=event_id, organizer=organizer)

  response = HttpResponse(content_type='text/csv')
  filename = f"{event.title.replace(' ', '_')}_attendees.csv"
  response['Content-Disposition'] = f'attachment; filename="{filename}"'

  writer = csv.writer(response)
  writer.writerow([
      'Ticket ID',
      'Attendee Name / Email',
      'Status',
      'Order Ref',
      'Total Price (GH₵)',
      'Booking Date',
  ])

  tickets = Ticket.objects.filter(event=event, payment_status='Paid').order_by(
      '-booking_date'
  )

  for ticket in tickets:
    attendee_name = (
        ticket.customer.user.username
        if ticket.customer
        else (ticket.guest_email or 'Guest')
    )
    status = 'Used (Scanned)' if ticket.is_used else 'Valid'

    writer.writerow([
        ticket.ticket_id,
        attendee_name,
        status,
        ticket.order_reference,
        ticket.total_price,
        ticket.booking_date.strftime('%Y-%m-%d %H:%M'),
    ])

  return response




import json
import hmac
import hashlib
import threading
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

@csrf_exempt
def payment_webhook(request):
    if request.method == 'POST':
        # 1. Verify the signature (Paystack example)
        paystack_signature = request.headers.get('x-paystack-signature')
        secret = settings.PAYSTACK_SECRET_KEY.encode('utf-8')
        
        computed_signature = hmac.new(
            secret, 
            request.body, 
            hashlib.sha512
        ).hexdigest()
        
        if paystack_signature != computed_signature:
            return HttpResponseBadRequest("Invalid signature")
            
        # 2. Parse the JSON event data
        payload = json.loads(request.body)
        
        if payload.get('event') == 'charge.success':
            reference = payload['data']['reference']
            
            # 3. Hand off the heavy processing to a background thread
            thread = threading.Thread(target=generate_ticket_task, args=(reference,))
            thread.start()

        # 4. Acknowledge fast
        return HttpResponse(status=200)

    return HttpResponseBadRequest("Invalid method")

import logging
from events . models import Ticket

logger = logging.getLogger(__name__)

def generate_ticket_task(reference):
    try:
        # 1. Find the pending ticket using the Paystack reference
        ticket = Ticket.objects.get(order_reference=reference)

        # 2. Prevent double-processing if Paystack retries the webhook
        if ticket.payment_status == 'Paid':
            logger.info(f"Ticket for reference {reference} is already paid. Skipping.")
            return

        # 3. Update the payment status
        ticket.payment_status = 'Paid'
        
        # 4. Save to database (This automatically triggers your custom save() 
        # method to generate the TKT-XXXXXX ticket_id if it doesn't exist yet)
        ticket.save()
        
        logger.info(f"Successfully verified payment and generated ticket {ticket.ticket_id} for {reference}")

        # 5. (Next Step) Send confirmation email to ticket.guest_email or ticket.customer.email
        # send_ticket_email(ticket)

    except Ticket.DoesNotExist:
        logger.error(f"Webhook received for unknown reference: {reference}")
    except Exception as e:
        logger.error(f"Fatal error processing ticket for {reference}: {str(e)}")

from django.shortcuts import render
from django.http import JsonResponse
from .models import Ticket

# Renders the waiting page after Paystack redirects the user
def verify_payment(request, reference):
    return render(request, 'events/verify_payment.html', {'reference': reference})# The API endpoint the JavaScript will poll every 3 seconds

def check_ticket_status(request, reference):
    try:
        ticket = Ticket.objects.get(order_reference=reference)
        return JsonResponse({
            'status': ticket.payment_status,
            'ticket_id': ticket.ticket_id
        })
    except Ticket.DoesNotExist:
        return JsonResponse({'error': 'Ticket not found'}, status=404)