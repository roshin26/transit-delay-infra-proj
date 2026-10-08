import csv
from django.core.management.base import BaseCommand, CommandError
from routes.models import Route


class Command(BaseCommand):
    help = "Load Dublin Bus routes from a GTFS static routes.txt file"

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to routes.txt')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        dublin_bus_agency_id = '1'

        try:
            f = open(csv_path, newline='', encoding='utf-8-sig')
        except FileNotFoundError:
            raise CommandError(f"File not found: {csv_path}")

        with f:
            reader = csv.DictReader(f)
            created_count = 0
            updated_count = 0

            for row in reader:
                if row['agency_id'] != dublin_bus_agency_id:
                    continue

                route, created = Route.objects.update_or_create(
                    route_id=row['route_id'],
                    defaults={
                        'short_name': row['route_short_name'],
                        'long_name': row['route_long_name'],
                        'mode': 'bus',
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created {created_count}, updated {updated_count} routes."
            )
        )