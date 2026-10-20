from django.utils import timezone
from prometheus_client import Gauge

from routes.models import FetchLog


def seconds_since_last_success():
    try:
        last = FetchLog.objects.filter(success=True).order_by('-fetched_at').first()
    except Exception:
        return float('inf')
    if last is None:
        return float('inf')
    return (timezone.now() - last.fetched_at).total_seconds()


data_age = Gauge(
    'transit_data_age_seconds',
    'Seconds since the last successful feed fetch',
)
# Runs the function every time Prometheus scrapes /metrics,
# so the value is always current and nothing needs updating by hand.
data_age.set_function(seconds_since_last_success)