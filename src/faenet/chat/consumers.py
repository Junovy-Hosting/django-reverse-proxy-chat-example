import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import ChatRoom, Message, Reaction
from .utils import is_valid_emoji


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat.

    Each WebSocket connection joins a channel layer group named after the
    chat room slug. Messages sent by any user are broadcast to all users
    in that group via Redis.
    """

    async def connect(self):
        self.room_slug = self.scope["url_route"]["kwargs"]["slug"]
        self.room_group_name = f"chat_{self.room_slug}"
        self.user = self.scope["user"]

        # Reject anonymous users
        if self.user.is_anonymous:
            await self.close()
            return

        # Join the room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Notify room that user joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "system_message",
                "message": f"{self.user.username} has entered the chamber",
            },
        )

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name") and not self.user.is_anonymous:
            # Notify room that user left
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "system_message",
                    "message": f"{self.user.username} has left the chamber",
                },
            )
            # Leave the room group
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type", "chat_message")

        if msg_type == "reaction":
            await self._handle_reaction(data)
        else:
            await self._handle_chat_message(data)

    async def _handle_chat_message(self, data):
        message = data.get("message", "").strip()
        if not message:
            return

        reply_to_id = data.get("reply_to")
        saved = await self.save_message(message, reply_to_id)

        broadcast = {
            "type": "chat_message",
            "message": message,
            "username": self.user.username,
            "message_id": saved["id"],
        }
        if saved["parent_id"]:
            broadcast["reply_to"] = {
                "message_id": saved["parent_id"],
                "username": saved["parent_username"],
                "content": saved["parent_content"][:100],
            }

        await self.channel_layer.group_send(self.room_group_name, broadcast)

    async def _handle_reaction(self, data):
        message_id = data.get("message_id")
        emoji = data.get("emoji", "")

        if not message_id or not emoji:
            return

        if not is_valid_emoji(emoji):
            return

        result = await self.toggle_reaction(message_id, emoji)
        if result is None:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "reaction_update",
                "message_id": message_id,
                "emoji": emoji,
                "action": result["action"],
                "username": self.user.username,
                "count": result["count"],
            },
        )

    async def chat_message(self, event):
        """Handle chat_message events from the channel layer."""
        payload = {
            "type": "chat",
            "message": event["message"],
            "username": event["username"],
            "message_id": event["message_id"],
        }
        if "reply_to" in event:
            payload["reply_to"] = event["reply_to"]
        await self.send(text_data=json.dumps(payload))

    async def reaction_update(self, event):
        """Handle reaction_update events from the channel layer."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "reaction_update",
                    "message_id": event["message_id"],
                    "emoji": event["emoji"],
                    "action": event["action"],
                    "username": event["username"],
                    "count": event["count"],
                }
            )
        )

    async def system_message(self, event):
        """Handle system_message events (join/leave notifications)."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "system",
                    "message": event["message"],
                }
            )
        )

    @database_sync_to_async
    def save_message(self, content, reply_to_id=None):
        room = ChatRoom.objects.get(slug=self.room_slug)
        parent = None
        if reply_to_id:
            try:
                parent = Message.objects.select_related("user").get(
                    id=reply_to_id, room=room
                )
            except Message.DoesNotExist:
                pass
        msg = Message.objects.create(
            room=room, user=self.user, content=content, parent=parent
        )
        result = {"id": msg.id, "parent_id": None, "parent_username": None, "parent_content": None}
        if parent:
            result["parent_id"] = parent.id
            result["parent_username"] = parent.user.username
            result["parent_content"] = parent.content
        return result

    @database_sync_to_async
    def toggle_reaction(self, message_id, emoji):
        try:
            room = ChatRoom.objects.get(slug=self.room_slug)
            message = Message.objects.get(id=message_id, room=room)
        except (ChatRoom.DoesNotExist, Message.DoesNotExist):
            return None

        existing = Reaction.objects.filter(
            message=message, user=self.user, emoji=emoji
        )
        if existing.exists():
            existing.delete()
            action = "remove"
        else:
            Reaction.objects.create(message=message, user=self.user, emoji=emoji)
            action = "add"

        count = Reaction.objects.filter(message=message, emoji=emoji).count()
        return {"action": action, "count": count}
