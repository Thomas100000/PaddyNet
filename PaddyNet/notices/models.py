from django.db import models
from django.conf import settings

class Notification(models.Model):
    title = models.CharField(
        max_length=255,
        help_text="Notification headline or subject"
    )
    message = models.TextField(
        help_text="Body content of the notification"
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posted_notifications',
        help_text="Admin who posted this notification"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when notification was published"
    )

    objects = models.Manager()

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        posted_by_name = getattr(self.posted_by, 'username', str(self.posted_by))
        return f"{self.title} (by {posted_by_name})"
