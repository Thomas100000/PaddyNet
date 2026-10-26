from typing import Any
from django.contrib import admin
from .models import Bill

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display: Any = ('id', 'farmer', 'amount', 'status', 'date_issued')
    list_filter: Any = ('status', 'date_issued')
    search_fields: Any = ('farmer__username', 'farmer__email', 'description')
