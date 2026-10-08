import os
import signal
import threading
import time

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections
from google.transit import gtfs_realtime_pb2

from routes.models import DelayReading, FetchLog, Route

FEED_URL = "https://api.nationaltransport.ie/gtfsr/v2/gtfsr"


class Command(BaseCommand):
    help = "Fetch live GTFS-Realtime delays for Dublin Bus routes (once, or in a loop)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--loop', action='store_true',
            help='Keep fetching until stopped (Ctrl+C)',
        )
        parser.add_argument(
            '--interval', type=int, default=60,
            help='Seconds between fetches in loop mode (default 60)',
        )

    def handle(self, *args, **options):
        api_key = os.environ.get('NTA_API_KEY')
        if not api_key:
            # CommandError makes the command exit with an error code,
            # which Docker and Kubernetes treat as a failed start.
            raise CommandError("NTA_API_KEY is not set in the environment")

        if not options['loop']:
            self.fetch_once(api_key)
            return

        # An Event lets us sleep between fetches but wake up immediately
        # when we are told to stop (Ctrl+C locally, SIGTERM in Docker/Kubernetes).
        stop = threading.Event()
        signal.signal(signal.SIGINT, lambda *_: stop.set())
        signal.signal(signal.SIGTERM, lambda *_: stop.set())

        interval = options['interval']
        self.stdout.write(f"Fetching every {interval}s. Press Ctrl+C to stop.")

        while not stop.is_set():
            started = time.monotonic()

            # Long-running processes can end up holding a database connection
            # the server has already closed. This discards any dead ones.
            close_old_connections()

            try:
                self.fetch_once(api_key)
            except Exception as exc:
                # One bad cycle must never kill the loop.
                self.stderr.write(self.style.ERROR(f"Unexpected error: {exc}"))

            # Sleep for the rest of the interval, so fetches start about
            # `interval` seconds apart regardless of how long each one took.
            elapsed = time.monotonic() - started
            stop.wait(max(0, interval - elapsed))

        self.stdout.write("Stopped.")

    def fetch_once(self, api_key):
        # Reload the Dublin Bus route IDs each cycle: it is one cheap query,
        # and it picks up routes added by load_routes without a restart.
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
            # A failed fetch is logged too: it feeds the freshness SLO later.
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

            # Dublin-only filter: the feed is nationwide.
            if route_id not in known_route_ids:
                continue

            # One reading per trip per fetch: the delay at the bus's next
            # stop with a delay value. This is the bus's "current delay",
            # and it keeps the table roughly 10x smaller than storing
            # every upcoming stop.
            for stu in trip_update.stop_time_update:
                delay_seconds = self.get_delay(stu)
                if delay_seconds is None:
                    continue

                readings.append(DelayReading(
                    route_id=route_id,
                    trip_id=trip_update.trip.trip_id,
                    stop_id=stu.stop_id,
                    delay_seconds=delay_seconds,
                ))
                break

        DelayReading.objects.bulk_create(readings, batch_size=500)

        FetchLog.objects.create(success=True, record_count=len(readings))

        self.stdout.write(self.style.SUCCESS(
            f"Saved {len(readings)} readings from {len(feed.entity)} feed entities."
        ))

    @staticmethod
    def get_delay(stop_time_update):
        """Return the delay in seconds for a stop update, or None if it has none."""
        if stop_time_update.HasField('arrival') and stop_time_update.arrival.HasField('delay'):
            return stop_time_update.arrival.delay
        if stop_time_update.HasField('departure') and stop_time_update.departure.HasField('delay'):
            return stop_time_update.departure.delay
        return None