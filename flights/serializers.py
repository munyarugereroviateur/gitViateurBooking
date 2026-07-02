from rest_framework import serializers
from .models import Flight, Booking


class FlightSerializer(serializers.ModelSerializer):
    aircraft_model = serializers.CharField(source='aircraft.model', read_only=True)
    seats_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Flight
        fields = ['id', 'flight_number', 'airline', 'origin', 'destination', 'departure_time',
                  'arrival_time', 'duration_minutes', 'aircraft_model', 'capacity',
                  'seats_available', 'price_per_seat', 'status']


class BookingSerializer(serializers.ModelSerializer):
    flight_number = serializers.CharField(source='flight.flight_number', read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'flight', 'flight_number', 'passenger', 'booking_date', 'seat_number',
                  'class_type', 'status', 'ticket_number']
        read_only_fields = ['ticket_number', 'booking_date']