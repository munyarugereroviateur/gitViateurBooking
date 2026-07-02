from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Flight, Booking
from .serializers import FlightSerializer, BookingSerializer
from .ml_utils import predict_delay_probability


class FlightViewSet(viewsets.ModelViewSet):
    queryset = Flight.objects.select_related('aircraft').all()
    serializer_class = FlightSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['get'])
    def delay_prediction(self, request, pk=None):
        flight = self.get_object()
        probability = predict_delay_probability(flight)
        return Response({'flight_number': flight.flight_number, 'delay_probability': probability})


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name='Airline Staff').exists():
            return Booking.objects.all()
        return Booking.objects.filter(passenger__user=user)