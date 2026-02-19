from django import forms

from .models import ChatRoom


class ChatRoomForm(forms.ModelForm):
    class Meta:
        model = ChatRoom
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-gray-100 focus:outline-none focus:border-purple-500",
                    "placeholder": "Enter chamber name...",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-gray-100 focus:outline-none focus:border-purple-500",
                    "rows": 3,
                    "placeholder": "Describe this chamber...",
                }
            ),
        }
