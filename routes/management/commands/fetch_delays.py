import os
import requests
from django.core.management.base import BaseCommand
from google.transit import gtfs_realtime_pb2

from routes.models import Route, DelayReading, FetchLog

FEED_URL = "https://api.nationaltransport.ie/gtfsr/v2/gtfsr"


class Command(BaseCommand):
    help = "Fetch live GTFS-Realtime delays and store readings for Dublin Bus routes"

    def handle(self, *args, **options):
        api_key = os.environ.get('NTA_API_KEY')
        if not api_key:
            self.stderr.write(self.style.ERROR("NTA_API_KEY not set in environment"))
            return

        known_route_ids = set(Route.objects.values_list('route_id', flat=True))

        try:
            response = requests.get(
                FEED_URL,
                headers={'x-api-key': api_key},
                timeout=15,
            )
            response.raise_for_status()

            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)

        except Exception as exc:
            
            FetchLog.objects.create(
                success=False,
                record_count=0,
                error_message=str(exc)[:500],
            )
            self.stderr.write(self.style.ERROR(f"Fetch failed: {exc}"))
            return

        readings = []

        for entity in feed.entity:
            if not entity.HasField('trip_update'):
                continue

            trip_update = entity.trip_update
            route_id = trip_update.trip.route_id

            # This is the Dublin-only filter: route_id in the live feed matches
            
            if route_id not in known_route_ids:
                continue

            trip_id = trip_update.trip.trip_id

            for stu in trip_update.stop_time_update:
                delay_seconds = None

                if stu.HasField('arrival') and stu.arrival.HasField('delay'):
                    delay_seconds = stu.arrival.delay
                elif stu.HasField('departure') and stu.departure.HasField('delay'):
                    delay_seconds = stu.departure.delay

                if delay_seconds is None:
                    continue

                readings.append(DelayReading(
                    route_id=route_id,
                    trip_id=trip_id,
                    stop_id=stu.stop_id,
                    delay_seconds=delay_seconds,
                ))

        # bulk_create sends one INSERT instead of one per row — matters here
        # since a single poll can produce thousands of readings.
        DelayReading.objects.bulk_create(readings, batch_size=500)

        FetchLog.objects.create(
            success=True,
            record_count=len(readings),
            error_message='',
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Saved {len(readings)} delay readings from {len(feed.entity)} feed entities."
            )
        )