from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
import joblib, pandas as pd
from django.conf import settings

from .models import Aircraft, Flight, Passenger, Booking
from .forms import AircraftForm, FlightForm, PassengerForm, BookingForm, RegisterForm
from .decorators import staff_required
from .ml_utils import predict_delay_probability


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        role = request.POST.get('role', 'Passenger')
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            group, _ = Group.objects.get_or_create(name=role)
            user.groups.add(group)
            if role == 'Passenger':
                Passenger.objects.create(
                    user=user, first_name=user.first_name, last_name=user.last_name,
                    date_of_birth='2000-01-01', nationality='Rwandan',
                    passport_number=f"TMP{user.id}", email=user.email,
                    phone_number='0000000000')
            messages.success(request, 'Account created. Please log in.')
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'flights/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        user = authenticate(request, username=request.POST['username'],
                             password=request.POST['password'])
        if user:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Invalid credentials.')
    return render(request, 'flights/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    is_staff_role = request.user.groups.filter(name='Airline Staff').exists()
    if is_staff_role:
        context = {
            'total_flights': Flight.objects.count(),
            'total_bookings': Booking.objects.count(),
            'total_aircraft': Aircraft.objects.count(),
            'total_passengers': Passenger.objects.count(),
        }
        return render(request, 'flights/dashboard_staff.html', context)
    else:
        passenger = getattr(request.user, 'passenger_profile', None)
        bookings = Booking.objects.filter(passenger=passenger) if passenger else []
        return render(request, 'flights/dashboard_passenger.html', {'bookings': bookings})


@login_required
def flight_list(request):
    query = request.GET.get('q', '')
    flights = Flight.objects.select_related('aircraft').all()
    if query:
        flights = flights.filter(
            Q(flight_number__icontains=query) | Q(origin__icontains=query) |
            Q(destination__icontains=query) | Q(airline__icontains=query))
    paginator = Paginator(flights.order_by('departure_time'), 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    flights_with_delay = []
    for f in page_obj:
        prob = predict_delay_probability(f)
        flights_with_delay.append({'flight': f, 'delay_probability': prob})
    return render(request, 'flights/flight_list.html',
                  {'flights_with_delay': flights_with_delay, 'page_obj': page_obj, 'query': query})


@staff_required
def flight_create(request):
    form = FlightForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Flight created.')
        return redirect('flight_list')
    return render(request, 'flights/flight_form.html', {'form': form, 'title': 'Add Flight'})


@staff_required
def flight_update(request, pk):
    flight = get_object_or_404(Flight, pk=pk)
    form = FlightForm(request.POST or None, request.FILES or None, instance=flight)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Flight updated.')
        return redirect('flight_list')
    return render(request, 'flights/flight_form.html', {'form': form, 'title': 'Edit Flight'})


@staff_required
def flight_delete(request, pk):
    flight = get_object_or_404(Flight, pk=pk)
    if request.method == 'POST':
        flight.delete()
        messages.success(request, 'Flight deleted.')
        return redirect('flight_list')
    return render(request, 'flights/flight_confirm_delete.html', {'flight': flight})
@login_required
def booking_create(request):
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.passenger = request.user.passenger_profile
            booking.ticket_number = f"TCK{Booking.objects.count() + 1:06d}"
            booking.save()
            messages.success(request, 'Booking confirmed!')
            return redirect('my_bookings')
    else:
        form = BookingForm()
    return render(request, 'flights/booking_form.html', {'form': form})


@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(passenger=request.user.passenger_profile).select_related('flight')
    return render(request, 'flights/my_bookings.html', {'bookings': bookings})


@login_required
def booking_cancel(request, pk):
    booking = get_object_or_404(Booking, pk=pk, passenger=request.user.passenger_profile)
    booking.status = 'Cancelled'
    booking.save()
    messages.success(request, 'Booking cancelled.')
    return redirect('my_bookings')


@login_required
def booking_checkin(request, pk):
    booking = get_object_or_404(Booking, pk=pk, passenger=request.user.passenger_profile)
    booking.status = 'Checked-in'
    booking.save()
    messages.success(request, 'Checked in successfully.')
    return redirect('my_bookings')


@staff_required
def all_bookings(request):
    query = request.GET.get('q', '')
    bookings = Booking.objects.select_related('flight', 'passenger').all()
    if query:
        bookings = bookings.filter(
            Q(ticket_number__icontains=query) | Q(passenger__last_name__icontains=query))
    return render(request, 'flights/all_bookings.html', {'bookings': bookings})