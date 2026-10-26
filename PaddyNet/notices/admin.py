from typing import Any
from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display: Any = ('title', 'posted_by', 'created_at')
    search_fields: Any = ('title', 'message', 'posted_by__username')
    list_filter: Any = ('created_at',)
