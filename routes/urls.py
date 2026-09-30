from django.urls import path
from . import views

urlpatterns = [
    path('', views.routes, name='routes'),
    path('<str:route_id>/', views.route_detail, name='route_detail'),
]