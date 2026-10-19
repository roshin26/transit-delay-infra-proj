from django.shortcuts import render 
from django.db import connection
from django.http import JsonResponse

def status(request):
    return render(request, 'status/status.html')

# Create your views here.
def healthz(request):
    return JsonResponse({'status': 'ok'})


def readyz(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:
        return JsonResponse({'status': 'database unavailable'}, status=503)
    return JsonResponse({'status': 'ready'})