from datetime import timedelta

from django.db.models import Avg, Count, Max, Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import DelayReading, Route

# A delay above this many seconds is shown in the warning colour (5 minutes).
WARNING_SECONDS = 300
# A reading counts as "on time" if it is at most this many seconds late (2 minutes).
ON_TIME_SECONDS = 120


def format_duration(seconds):
    """Turn a number of seconds into text like '3m 40s'."""
    seconds = round(seconds or 0)
    sign = '-' if seconds < 0 else ''
    seconds = abs(seconds)
    return f"{sign}{seconds // 60}m {seconds % 60:02d}s"


def add_bar_widths(rows, key='avg_delay'):
    """
    Give each row a delay_display, is_warning and bar_pct (0-100, relative to
    the worst row). Works on a list of dicts or a list of model instances.
    """
    def get(row, name):
        return row[name] if isinstance(row, dict) else getattr(row, name)

    def put(row, name, value):
        if isinstance(row, dict):
            row[name] = value
        else:
            setattr(row, name, value)

    values = [get(r, key) for r in rows if get(r, key) is not None]
    worst = max(values, default=0)

    for row in rows:
        value = get(row, key)
        if value is None:
            put(row, 'delay_display', None)
            put(row, 'is_warning', False)
            put(row, 'bar_pct', 0)
            continue
        put(row, 'delay_display', format_duration(value))
        put(row, 'is_warning', value > WARNING_SECONDS)
        put(row, 'bar_pct', max(5, round(value / worst * 100)) if worst > 0 else 0)


def routes_list(request):
    q = request.GET.get('q', '').strip()
    since = timezone.now() - timedelta(hours=1)

    routes = Route.objects.annotate(
        avg_delay=Avg(
            'delay_readings__delay_seconds',
            filter=Q(delay_readings__recorded_at__gte=since),
        )
    ).order_by('short_name')

    if q:
        routes = routes.filter(
            Q(short_name__icontains=q) | Q(long_name__icontains=q)
        )

    routes = list(routes)
    add_bar_widths(routes)

    return render(request, 'routes/routes.html', {'routes': routes, 'q': q})


def route_detail(request, route_id):
    route = get_object_or_404(Route, route_id=route_id)
    since = timezone.now() - timedelta(hours=1)
    readings = DelayReading.objects.filter(route=route, recorded_at__gte=since)

    total = readings.count()
    on_time = readings.filter(delay_seconds__lte=ON_TIME_SECONDS).count()
    avg_delay = readings.aggregate(avg=Avg('delay_seconds'))['avg']

    stops = list(
        readings
        .values('stop_id')
        .annotate(
            avg_delay=Avg('delay_seconds'),
            max_delay=Max('delay_seconds'),
            reading_count=Count('id'),
        )
        .order_by('-avg_delay')[:10]
    )
    add_bar_widths(stops)
    for stop in stops:
        stop['max_display'] = format_duration(stop['max_delay'])

    context = {
        'route': route,
        'total_readings': total,
        'active_vehicles': readings.values('trip_id').distinct().count(),
        'avg_delay_display': format_duration(avg_delay) if avg_delay is not None else None,
        'avg_delay_warning': avg_delay is not None and avg_delay > WARNING_SECONDS,
        'on_time_pct': round(on_time / total * 100, 1) if total else None,
        'stops': stops,
    }
    return render(request, 'routes/route_detail.html', context)