from django.contrib import admin
from .models import Aircraft, Flight, Passenger, Booking

admin.site.site_header = 'Airline Flight Booking System'
admin.site.site_title = 'Airline Flight Booking System Admin'
admin.site.index_title = 'Welcome to Booking Airlines Admin Portal'

admin.site.register(Aircraft)
admin.site.register(Flight)
admin.site.register(Passenger)
admin.site.register(Booking)