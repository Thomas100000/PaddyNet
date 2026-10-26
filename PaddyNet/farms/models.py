from django.db import models
from django.conf import settings
from django.db.models import Sum

class FarmerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='farmer_profile'
    )
    full_name = models.CharField(max_length=255, blank=True, default='')
    village = models.CharField(max_length=255, default='Kainakary')
    phone_number = models.CharField(max_length=20)
    acres_owned = models.DecimalField(max_digits=7, decimal_places=2, default=0.0)
    farming_group = models.CharField(max_length=100, default='A BLOCK')
    farmer_id = models.CharField(max_length=50, unique=True, null=True, blank=True, help_text="Unique Farmer ID starting with PDN")
    is_verified = models.BooleanField(default=False)

    objects = models.Manager()

    def __str__(self):
        name_str = self.full_name if self.full_name else getattr(self.user, 'username', str(self.user))
        return f"Farmer Profile: {name_str} - {self.village} ({'Verified' if self.is_verified else 'Pending'})"


class Field(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fields',
        limit_choices_to={'role': 'FARMER'},
        help_text="Farmer who owns and manages this field"
    )
    field_name = models.CharField(max_length=150, help_text="Descriptive name of the field (e.g. North Polder, Block 4)")
    location = models.CharField(max_length=255, help_text="Village, padasekharam, or survey location")
    extent_area = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        help_text="Extent or area of the field in acres"
    )
    field_identifier = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Optional survey number or field code (e.g. SY-104/2)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        code_str = f" [{self.field_identifier}]" if self.field_identifier else ""
        return f"{self.field_name}{code_str} ({self.extent_area} acres)"

    @property
    def total_harvest_yield(self):
        activities = getattr(self, 'activities', None)
        if activities is not None:
            harvest_sum = activities.filter(activity_type=FarmingActivity.ActivityType.HARVEST).aggregate(total=Sum('yield_kg'))['total']
            return harvest_sum or 0
        return 0


class FarmingActivity(models.Model):
    class ActivityType(models.TextChoices):
        SOWING = 'SOWING', 'Sowing'
        TRANSPLANTING = 'TRANSPLANTING', 'Transplanting'
        FERTILIZER = 'FERTILIZER', 'Fertilizer Application'
        PESTICIDE = 'PESTICIDE', 'Pesticide Application'
        IRRIGATION = 'IRRIGATION', 'Irrigation'
        HARVEST = 'HARVEST', 'Harvest'

    field = models.ForeignKey(
        Field,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices,
        help_text="Type of farming activity performed"
    )
    activity_date = models.DateField(help_text="Date when activity took place")
    season_year = models.CharField(
        max_length=50,
        help_text="Season and year (e.g. 2025 Kharif, 2025 Rabi, 2024-25 Mundakan)"
    )
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Specific observations, inputs used, fertilizer types, dosage, irrigation source, etc."
    )
    yield_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Yield in kilograms (relevant for Harvest activities)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        ordering = ['activity_date', 'created_at']

    def __str__(self):
        return f"{self.get_activity_type_display()} on {self.activity_date} ({self.field.field_name})"
