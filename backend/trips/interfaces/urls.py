from django.urls import path

from .api import views

urlpatterns = [
    path("health/", views.health),
    path("geocode/", views.geocode_view),
    path("trips/", views.trip_create),
    path("trips/<uuid:trip_id>/", views.trip_detail),
    path("trips/<uuid:trip_id>/heatmap/", views.trip_heatmap),
]
