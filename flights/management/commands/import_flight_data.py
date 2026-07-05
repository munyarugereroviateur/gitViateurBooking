"""
SkyBook - Import Flight Dataset into Database
===============================================
Place in: flights/management/commands/import_flight_data.py

Matched to the real models:

class Aircraft(models.Model):
    model, registration_number, manufacturer, capacity,
    year_manufactured, last_maintenance

class Flight(models.Model):
    flight_number, airline, origin, destination,
    departure_time (DateTimeField), arrival_time, duration_minutes,
    aircraft (FK), capacity, price_per_seat, status, document

Run with:
    python manage.py import_flight_data --csv-path "<path>" --limit 500
"""

import datetime
import pandas as pd
from django.core.management.base import BaseCommand
from django.utils import timezone

from flights.models import Aircraft, Flight


class Command(BaseCommand):
    help = "Import flight records from US_flights_2023.csv into the database"

    def add_arguments(self, parser):
        parser.add_argument("--csv-path", type=str, required=True)
        parser.add_argument("--limit", type=int, default=None)

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        limit = options["limit"]

        self.stdout.write(f"Reading {csv_path} ...")
        df = pd.read_csv(csv_path)
        df["FlightDate"] = pd.to_datetime(df["FlightDate"])
        if limit:
            df = df.sample(n=min(limit, len(df)), random_state=42)

        aircraft_cache = {}
        created_flights = 0
        skipped = 0
        used_flight_numbers = set(Flight.objects.values_list("flight_number", flat=True))

        for idx, row in df.iterrows():
            try:
                year_built = 2024 - int(row["Aicraft_age"])
                aircraft_key = (row["Manufacturer"], row["Model"], year_built)
                aircraft = aircraft_cache.get(aircraft_key)
                if aircraft is None:
                    reg_number = f"{row['Tail_Number']}"
                    aircraft, _ = Aircraft.objects.get_or_create(
                        registration_number=reg_number,
                        defaults={
                            "model": row["Model"],
                            "manufacturer": row["Manufacturer"],
                            "capacity": 180,
                            "year_manufactured": year_built,
                            "last_maintenance": datetime.date.today(),
                        },
                    )
                    aircraft_cache[aircraft_key] = aircraft

                base_number = f"{row['Airline'][:2].upper()}{idx % 9999:04d}"
                flight_number = base_number
                suffix = 0
                while flight_number in used_flight_numbers:
                    suffix += 1
                    flight_number = f"{base_number}-{suffix}"
                used_flight_numbers.add(flight_number)

                hour_map = {"Morning": 8, "Afternoon": 14, "Evening": 18, "Night": 22}
                hour = hour_map.get(row["DepTime_label"], 12)
                departure_dt = timezone.make_aware(
                    datetime.datetime.combine(row["FlightDate"].date(), datetime.time(hour, 0))
                )
                duration = int(row["Flight_Duration"]) if pd.notna(row["Flight_Duration"]) else 120
                arrival_dt = departure_dt + datetime.timedelta(minutes=duration)

                Flight.objects.create(
                    flight_number=flight_number,
                    airline=row["Airline"],
                    origin=row["Dep_Airport"],
                    destination=row["Arr_Airport"],
                    departure_time=departure_dt,
                    arrival_time=arrival_dt,
                    duration_minutes=duration,
                    aircraft=aircraft,
                    capacity=180,
                    price_per_seat=250.00,
                    status="Scheduled",
                )
                created_flights += 1

            except Exception as e:
                skipped += 1
                self.stderr.write(f"Skipped row {idx} due to error: {e}")

            if created_flights % 100 == 0 and created_flights > 0:
                self.stdout.write(f"  ... {created_flights} flights imported")

        self.stdout.write(self.style.SUCCESS(
            f"Done. Imported {created_flights} flights, skipped {skipped}."
        ))