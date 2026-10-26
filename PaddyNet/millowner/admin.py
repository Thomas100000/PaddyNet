from typing import Any
from django.contrib import admin
from .models import MillOwnerProfile, Bid

@admin.register(MillOwnerProfile)
class MillOwnerProfileAdmin(admin.ModelAdmin):
    list_display: Any = ('user', 'mill_name', 'mill_location', 'phone_number', 'fssai_license_number', 'is_verified')
    list_filter: Any = ('is_verified', 'mill_location')
    search_fields: Any = ('user__username', 'mill_name', 'phone_number', 'fssai_license_number')

@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display: Any = ('id', 'millowner', 'field', 'amount', 'status', 'counter_amount', 'date')
    list_filter: Any = ('status', 'date', 'field__location')
    search_fields: Any = ('millowner__username', 'field__field_name', 'notes', 'farmer_note')

