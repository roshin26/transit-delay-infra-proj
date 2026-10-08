from django.shortcuts import render
from django.db.models import Avg, Count
from django.utils import timezone
from datetime import timedelta

from routes.models import Route, DelayReading, FetchLog


def format_duration(seconds):
    seconds = round(seconds or 0)
    sign = '-' if seconds < 0 else ''
    seconds = abs(seconds)
    return f"{sign}{seconds // 60}m {seconds % 60:02d}s"


def index(request):
    since = timezone.now() - timedelta(hours=1)
    recent = DelayReading.objects.filter(recorded_at__gte=since)

    route_stats = (
        recent
        .values('route__route_id', 'route__short_name', 'route__long_name')
        .annotate(avg_delay=Avg('delay_seconds'), reading_count=Count('id'))
        .order_by('-avg_delay')
    )

    top = list(route_stats[:10])
    max_delay = max((r['avg_delay'] for r in top), default=0)
    for r in top:
        r['delay_display'] = format_duration(r['avg_delay'])
        r['is_warning'] = r['avg_delay'] > 300
        r['bar_pct'] = max(5, round(r['avg_delay'] / max_delay * 100)) if max_delay > 0 else 0

    total_count = recent.count()
    on_time_count = recent.filter(delay_seconds__lte=120).count()
    overall_avg = recent.aggregate(avg=Avg('delay_seconds'))['avg']

    context = {
        'on_time_pct': round(on_time_count / total_count * 100, 1) if total_count else 0,
        'avg_delay_display': format_duration(overall_avg),
        'vehicles_tracked': recent.values('trip_id').distinct().count(),
        'routes_tracked': Route.objects.count(),
        'most_delayed': top[0] if top else None,
        'top_delayed_routes': top,
        'latest_fetch': FetchLog.objects.first(),
    }
    return render(request, 'home/index.html', context)