from django.contrib import admin

from .models import ChatRoom, Message, Reaction


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_by", "created_at"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["room", "user", "content", "created_at", "parent"]
    list_filter = ["room", "user"]
    raw_id_fields = ["parent"]


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ["message", "user", "emoji", "created_at"]
    list_filter = ["emoji"]
