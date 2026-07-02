from django import forms
from django.contrib.auth.models import User
from .models import Aircraft, Flight, Passenger, Booking
import datetime


class AircraftForm(forms.ModelForm):
    class Meta:
        model = Aircraft
        fields = '__all__'
        widgets = {'last_maintenance': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})}

    def clean_year_manufactured(self):
        year = self.cleaned_data['year_manufactured']
        if year < 1950 or year > datetime.date.today().year:
            raise forms.ValidationError("Enter a realistic manufacturing year.")
        return year


class FlightForm(forms.ModelForm):
    class Meta:
        model = Flight
        fields = '__all__'
        widgets = {
            'departure_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'arrival_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }

    def clean(self):
        cleaned = super().clean()
        dep = cleaned.get('departure_time')
        arr = cleaned.get('arrival_time')
        if dep and arr and arr <= dep:
            raise forms.ValidationError("Arrival time must be after departure time.")
        return cleaned


class PassengerForm(forms.ModelForm):
    class Meta:
        model = Passenger
        exclude = ['user']
        widgets = {'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})}

    def clean_passport_number(self):
        passport = self.cleaned_data['passport_number']
        if len(passport) < 5:
            raise forms.ValidationError("Passport number looks too short.")
        return passport


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['flight', 'seat_number', 'class_type']

    def clean(self):
        cleaned = super().clean()
        flight = cleaned.get('flight')
        seat = cleaned.get('seat_number')
        if flight and flight.seats_available <= 0:
            raise forms.ValidationError("This flight is fully booked.")
        if flight and seat and Booking.objects.filter(flight=flight, seat_number=seat,
                                                        status__in=['Confirmed', 'Checked-in']).exists():
            raise forms.ValidationError("This seat is already taken on this flight.")
        return cleaned


class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = ''

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('confirm_password'):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user