from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Aircraft(models.Model):
    model = models.CharField(max_length=100)
    registration_number = models.CharField(max_length=20, unique=True)
    manufacturer = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField()
    year_manufactured = models.PositiveIntegerField()
    last_maintenance = models.DateField()

    def __str__(self):
        return f"{self.registration_number} ({self.model})"


class Flight(models.Model):
    STATUS_CHOICES = [
        ('Scheduled', 'Scheduled'),
        ('Delayed', 'Delayed'),
        ('Cancelled', 'Cancelled'),
        ('Completed', 'Completed'),
    ]
    flight_number = models.CharField(max_length=10, unique=True)
    airline = models.CharField(max_length=100)
    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()
    aircraft = models.ForeignKey(Aircraft, on_delete=models.CASCADE, related_name='flights')
    capacity = models.PositiveIntegerField()
    price_per_seat = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Scheduled')
    document = models.FileField(upload_to='flight_docs/', blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['origin', 'destination']),
            models.Index(fields=['departure_time']),
        ]

    def __str__(self):
        return f"{self.flight_number}: {self.origin} -> {self.destination}"

    @property
    def seats_booked(self):
        return self.bookings.filter(status__in=['Confirmed', 'Checked-in']).count()

    @property
    def seats_available(self):
        return self.capacity - self.seats_booked


class Passenger(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='passenger_profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    nationality = models.CharField(max_length=100)
    passport_number = models.CharField(max_length=30, unique=True)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    profile_picture = models.ImageField(upload_to='passenger_photos/', blank=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Booking(models.Model):
    CLASS_CHOICES = [('Economy', 'Economy'), ('Business', 'Business'), ('First', 'First')]
    STATUS_CHOICES = [('Confirmed', 'Confirmed'), ('Cancelled', 'Cancelled'), ('Checked-in', 'Checked-in')]

    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name='bookings')
    passenger = models.ForeignKey(Passenger, on_delete=models.CASCADE, related_name='bookings')
    booking_date = models.DateTimeField(auto_now_add=True)
    seat_number = models.CharField(max_length=5)
    class_type = models.CharField(max_length=10, choices=CLASS_CHOICES, default='Economy')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Confirmed')
    ticket_number = models.CharField(max_length=20, unique=True)

    class Meta:
        unique_together = ('flight', 'seat_number')

    def __str__(self):
        return f"{self.ticket_number} - {self.passenger} on {self.flight.flight_number}"