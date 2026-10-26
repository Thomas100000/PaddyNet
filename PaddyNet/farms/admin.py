from typing import Any
from django.contrib import admin
from .models import FarmerProfile, Field, FarmingActivity

@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display: Any = ('user', 'farmer_id', 'village', 'farming_group', 'acres_owned', 'is_verified')
    list_filter: Any = ('is_verified', 'village', 'farming_group')
    search_fields: Any = ('user__username', 'full_name', 'farmer_id', 'phone_number')

class FarmingActivityInline(admin.TabularInline):
    model = FarmingActivity
    extra = 1

@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display: Any = ('field_name', 'owner', 'location', 'extent_area', 'field_identifier', 'created_at')
    list_filter: Any = ('location', 'created_at')
    search_fields: Any = ('field_name', 'owner__username', 'field_identifier', 'location')
    inlines: Any = [FarmingActivityInline]

@admin.register(FarmingActivity)
class FarmingActivityAdmin(admin.ModelAdmin):
    list_display: Any = ('field', 'activity_type', 'activity_date', 'season_year', 'yield_kg', 'created_at')
    list_filter: Any = ('activity_type', 'season_year', 'activity_date')
    search_fields: Any = ('field__field_name', 'season_year', 'notes')
