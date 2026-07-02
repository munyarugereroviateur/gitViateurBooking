from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .api_views import FlightViewSet, BookingViewSet

router = DefaultRouter()
router.register('flights', FlightViewSet, basename='api-flights')
router.register('bookings', BookingViewSet, basename='api-bookings')

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('flights/', views.flight_list, name='flight_list'),
    path('flights/add/', views.flight_create, name='flight_create'),
    path('flights/<int:pk>/edit/', views.flight_update, name='flight_update'),
    path('flights/<int:pk>/delete/', views.flight_delete, name='flight_delete'),

    path('bookings/new/', views.booking_create, name='booking_create'),
    path('bookings/mine/', views.my_bookings, name='my_bookings'),
    path('bookings/<int:pk>/cancel/', views.booking_cancel, name='booking_cancel'),
    path('bookings/<int:pk>/checkin/', views.booking_checkin, name='booking_checkin'),
    path('bookings/all/', views.all_bookings, name='all_bookings'),

    path('api/', include(router.urls)),
]