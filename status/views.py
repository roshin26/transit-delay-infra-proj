from django.shortcuts import render 

def status(request):
    return render(request, 'status/status.html')

# Create your views here.
