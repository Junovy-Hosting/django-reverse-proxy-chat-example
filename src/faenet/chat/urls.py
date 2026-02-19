from django.urls import path

from . import views

urlpatterns = [
    path("", views.room_list, name="room_list"),
    path("rooms/new/", views.room_create, name="room_create"),
    path("rooms/<slug:slug>/", views.room_detail, name="room_detail"),
    path("api/giphy/search/", views.giphy_search, name="giphy_search"),
]
