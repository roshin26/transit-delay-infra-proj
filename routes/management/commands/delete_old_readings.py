from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from routes.models import DelayReading, FetchLog

BATCH_SIZE = 5000


class Command(BaseCommand):
    help = "Delete delay readings and fetch logs older than a retention period"

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=7,
            help='Keep delay readings for this many days (default 7)',
        )
        parser.add_argument(
            '--log-days', type=int, default=30,
            help='Keep fetch logs for this many days (default 30)',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be deleted without deleting anything',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        dry_run = options['dry_run']

        targets = [
            ('delay readings', DelayReading.objects.filter(
                recorded_at__lt=now - timedelta(days=options['days'])
            )),
            ('fetch logs', FetchLog.objects.filter(
                fetched_at__lt=now - timedelta(days=options['log_days'])
            )),
        ]

        for label, queryset in targets:
            if dry_run:
                self.stdout.write(f"Would delete {queryset.count()} {label}.")
                continue

            deleted = self.delete_in_batches(queryset)
            self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} {label}."))

    @staticmethod
    def delete_in_batches(queryset):
        """
        Delete in chunks instead of one huge DELETE. A single statement that
        removes millions of rows can lock the table and stall the fetcher
        and the website while it runs.
        """
        model = queryset.model
        total = 0
        while True:
            pks = list(queryset.values_list('pk', flat=True)[:BATCH_SIZE])
            if not pks:
                return total
            model.objects.filter(pk__in=pks).delete()
            total += len(pks)