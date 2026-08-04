from django.db import models


class Notification(models.Model):
    """Chatbot report/notification record backed by existing ERP identities."""

    sender = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.CASCADE,
        related_name="chatbot_notifications_sent",
    )
    receiver = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.CASCADE,
        related_name="chatbot_notifications_received",
    )
    student = models.ForeignKey(
        "user_accounts.StudentDetails",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chatbot_notifications",
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Compatibility with deployments that already created the legacy
        # chatbot table. This integration never creates or alters ERP schema.
        managed = False
        db_table = "chatbot_notification"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["receiver", "is_read", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.sender_id} -> {self.receiver_id}: {self.message[:60]}"
