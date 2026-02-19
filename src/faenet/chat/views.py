from collections import defaultdict

import httpx
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ChatRoomForm
from .models import ChatRoom, Reaction


@login_required
def room_list(request):
    rooms = ChatRoom.objects.all()
    return render(request, "chat/room_list.html", {"rooms": rooms})


@login_required
def room_detail(request, slug):
    room = get_object_or_404(ChatRoom, slug=slug)
    chat_messages = (
        room.messages
        .select_related("user", "parent", "parent__user")
        .prefetch_related(
            Prefetch(
                "reactions",
                queryset=Reaction.objects.select_related("user"),
            )
        )
        .order_by("-created_at")[:50]
    )
    # Reverse so oldest is first in the template
    chat_messages = list(reversed(chat_messages))

    # Build reaction summaries per message
    current_username = request.user.username
    for msg in chat_messages:
        emoji_data = defaultdict(lambda: {"count": 0, "reacted_by_me": False})
        for r in msg.reactions.all():
            emoji_data[r.emoji]["count"] += 1
            if r.user.username == current_username:
                emoji_data[r.emoji]["reacted_by_me"] = True
        msg.reaction_list = [
            {"emoji": emoji, "count": d["count"], "reacted_by_me": d["reacted_by_me"]}
            for emoji, d in emoji_data.items()
        ]

    return render(request, "chat/room_detail.html", {"room": room, "chat_messages": chat_messages})


@login_required
def room_create(request):
    if request.method == "POST":
        form = ChatRoomForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.created_by = request.user
            room.save()
            return redirect("room_detail", slug=room.slug)
    else:
        form = ChatRoomForm()
    return render(request, "chat/room_create.html", {"form": form})


@login_required
def giphy_search(request):
    api_key = getattr(settings, "GIPHY_API_KEY", "")
    if not api_key:
        return JsonResponse({"error": "Giphy not configured"}, status=503)
    q = request.GET.get("q", "").strip()
    endpoint = "search" if q else "trending"
    params = {"api_key": api_key, "limit": 20, "rating": "pg-13"}
    if q:
        params["q"] = q
    resp = httpx.get(f"https://api.giphy.com/v1/gifs/{endpoint}", params=params)
    data = resp.json().get("data", [])
    results = [
        {
            "id": g["id"],
            "title": g.get("title", ""),
            "url": g["images"]["original"]["url"],
            "preview_url": g["images"]["fixed_height_small"]["url"],
        }
        for g in data
    ]
    return JsonResponse(results, safe=False)
