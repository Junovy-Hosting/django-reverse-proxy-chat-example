import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chat", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="replies",
                to="chat.message",
            ),
        ),
        migrations.CreateModel(
            name="Reaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("emoji", models.CharField(max_length=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reactions",
                        to="chat.message",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chat_reactions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["message", "emoji"],
                        name="idx_reaction_msg_emoji",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("message", "user", "emoji"),
                        name="unique_user_reaction_per_emoji",
                    ),
                ],
            },
        ),
    ]
