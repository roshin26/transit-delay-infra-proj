import csv

from django.core.management.base import BaseCommand, CommandError

from routes.models import Stop

BATCH_SIZE = 1000


class Command(BaseCommand):
    help = "Load bus stop names from a GTFS static stops.txt file"

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to stops.txt')

    def handle(self, *args, **options):
        csv_path = options['csv_path']

        try:
            f = open(csv_path, newline='', encoding='utf-8-sig')
        except FileNotFoundError:
            raise CommandError(f"File not found: {csv_path}")

        batch = []
        total = 0

        with f:
            for row in csv.DictReader(f):
                batch.append(Stop(stop_id=row['stop_id'], name=row['stop_name']))

                if len(batch) >= BATCH_SIZE:
                    self.save_batch(batch)
                    total += len(batch)
                    batch = []

        if batch:
            self.save_batch(batch)
            total += len(batch)

        self.stdout.write(self.style.SUCCESS(f"Done. Loaded {total} stops."))

    @staticmethod
    def save_batch(batch):
        # update_conflicts makes this safe to rerun: existing stops are updated
        # instead of causing a duplicate-key error (same idea as update_or_create
        # in load_routes, but done in bulk because there are thousands of stops).
        Stop.objects.bulk_create(
            batch,
            update_conflicts=True,
            unique_fields=['stop_id'],
            update_fields=['name'],
        )