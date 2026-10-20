from datetime import timedelta

from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from routes.models import DelayReading, FetchLog

from .metrics import seconds_since_last_success

# The freshness SLO: data should never be older than FRESH_SECONDS,
# and that should hold for at least SLO_TARGET_PCT of the time.
FRESH_SECONDS = 120
SLO_TARGET_PCT = 99.0
WINDOW_HOURS = 24


def healthz(request):
    """Liveness: the app is running."""
    return JsonResponse({'status': 'ok'})


def readyz(request):
    """Readiness: the app can reach its database."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:
        return JsonResponse({'status': 'database unavailable'}, status=503)
    return JsonResponse({'status': 'ready'})


def compute_freshness(success_times, now, max_age=FRESH_SECONDS):
    """
    Percentage of time the data was fresh (at most `max_age` seconds old).

    After each successful fetch the data's age grows from 0 until the next
    successful fetch. So each gap between fetches contributes
    min(gap, max_age) seconds of "fresh" time. We measure from the first
    fetch in the window until now, so time before the project started
    isn't counted against it.
    """
    if not success_times:
        return None

    total = (now - success_times[0]).total_seconds()
    if total <= 0:
        return None

    fresh = 0.0
    for prev, nxt in zip(success_times, success_times[1:]):
        fresh += min((nxt - prev).total_seconds(), max_age)
    fresh += min((now - success_times[-1]).total_seconds(), max_age)

    return round(fresh / total * 100, 1)


def format_age(seconds):
    """Turn seconds into short text like '28s', '3m 12s' or '2h 05m'."""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60:02d}s"
    return f"{seconds // 3600}h {(seconds % 3600) // 60:02d}m"


def status_page(request):
    now = timezone.now()
    since = now - timedelta(hours=WINDOW_HOURS)

    latest = FetchLog.objects.first()
    last_success = FetchLog.objects.filter(success=True).first()

    age = seconds_since_last_success()
    data_age = format_age(age) if age != float('inf') else None

    if latest is None:
        feed_status = 'none'
    elif not latest.success:
        feed_status = 'failed'
    elif age > FRESH_SECONDS:
        feed_status = 'stale'
    else:
        feed_status = 'healthy'

    success_times = list(
        FetchLog.objects
        .filter(success=True, fetched_at__gte=since)
        .order_by('fetched_at')
        .values_list('fetched_at', flat=True)
    )
    slo_pct = compute_freshness(success_times, now)

    recent_fetches = FetchLog.objects.filter(fetched_at__gte=since)
    fetch_total = recent_fetches.count()
    fetch_ok = recent_fetches.filter(success=True).count()

    oldest_reading = (
        DelayReading.objects.order_by('recorded_at')
        .values_list('recorded_at', flat=True)
        .first()
    )

    context = {
        'feed_status': feed_status,
        'data_age': data_age,
        'last_success': last_success,
        'slo_pct': slo_pct,
        'slo_met': slo_pct is not None and slo_pct >= SLO_TARGET_PCT,
        'slo_target': SLO_TARGET_PCT,
        'fresh_seconds': FRESH_SECONDS,
        'window_hours': WINDOW_HOURS,
        'fetch_total': fetch_total,
        'fetch_ok': fetch_ok,
        'fetch_success_pct': round(fetch_ok / fetch_total * 100, 1) if fetch_total else None,
        'readings_total': DelayReading.objects.count(),
        'oldest_reading': oldest_reading,
        'recent_failures': FetchLog.objects.filter(success=False)[:5],
    }
    return render(request, 'status/status.html', context)