from django.db import models
from django.conf import settings
from farms.models import Field

class MillOwnerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='millowner_profile'
    )
    mill_name = models.CharField(max_length=255)
    mill_location = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    fssai_license_number = models.CharField(
        max_length=14,
        unique=True,
        null=True,
        blank=True,
        help_text="14-digit FSSAI License Number"
    )
    is_verified = models.BooleanField(default=False)

    objects = models.Manager()

    def __str__(self):
        return f"Mill Owner Profile: {self.mill_name} ({self.fssai_license_number}) - {'Verified' if self.is_verified else 'Pending'}"


class Bid(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        BARGAINING = 'BARGAINING', 'Bargaining / Counter-Offer'

    millowner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bids',
        limit_choices_to={'role': 'MILLOWNER'},
        help_text="Mill owner who placed this bid"
    )
    field = models.ForeignKey(
        Field,
        on_delete=models.CASCADE,
        related_name='bids',
        help_text="Field / harvest produce lot being bid on"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total bid offer amount in ₹"
    )
    per_kg_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Offer rate per kg in ₹"
    )
    date = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the bid was placed"
    )
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Optional notes or terms for the offer (e.g. pickup logistics, payment terms)"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Decision status of this bid"
    )
    counter_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Farmer counter-offer amount in ₹"
    )
    counter_per_kg_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Farmer counter-offer per kg rate in ₹"
    )
    farmer_note = models.TextField(
        blank=True,
        default='',
        help_text="Farmer's bargaining remarks or notes to the mill owner"
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the farmer responded to this bid"
    )

    objects = models.Manager()

    class Meta:
        ordering = ['-date', '-amount']

    def __str__(self):
        profile = getattr(self.millowner, 'millowner_profile', None)
        name = profile.mill_name if profile and profile.mill_name else self.millowner.username
        field_name = getattr(self.field, 'field_name', 'Field')
        return f"Bid ₹{self.amount} on {field_name} by {name}"



