from django.urls import path

from . import views
from .pwa import manifest, pwa_icon, service_worker

urlpatterns = [
    path("sw.js", service_worker, name="service_worker"),
    path("manifest.json", manifest, name="pwa_manifest"),
    path("pwa/icon-<int:size>.svg", pwa_icon, name="pwa_icon"),
    path("", views.room_list, name="room_list"),
    path("rooms/new/", views.room_create, name="room_create"),
    path("rooms/<slug:slug>/", views.room_detail, name="room_detail"),
    path("api/giphy/search/", views.giphy_search, name="giphy_search"),
]
