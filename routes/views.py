from django.shortcuts import render


def routes(request):
    return render(request, 'routes/routes.html')

def route_detail(request, route_id):
    return render(request, 'routes/route_detail.html', {'route_id': route_id})
