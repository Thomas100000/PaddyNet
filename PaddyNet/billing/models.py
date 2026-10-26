import os
from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator


class Bill(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'
        DISPUTED = 'DISPUTED', 'Disputed'

    class BillCategory(models.TextChoices):
        BUND_MAINTENANCE = 'Bund Maintenance', 'Bund Maintenance'
        TRACTOR_BILL = 'Tractor Bill', 'Tractor Bill'
        SEEDS_BILL = 'Seeds Bill', 'Seeds Bill'
        HARVESTER_BILL = 'Harvester Bill', 'Harvester Bill'
        WATER_PUMPING = 'Water Pumping', 'Water Pumping'
        FERTILIZER_BILL = 'Fertilizer Bill', 'Fertilizer Bill'
        PESTICIDES_BILL = 'Pesticides Bill', 'Pesticides Bill'
        DRAINAGE_DEWATERING = 'Drainage & Dewatering Charges', 'Drainage & Dewatering Charges'
        POLDER_PUMPING = 'Polder Pumping Electricity Bill', 'Polder Pumping Electricity Bill'
        OTHER = 'Other Charges', 'Other Charges'

    farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bills',
        limit_choices_to={'role': 'FARMER'},
        help_text="Farmer associated with this bill"
    )
    description = models.CharField(
        max_length=255,
        choices=BillCategory.choices,
        default=BillCategory.BUND_MAINTENANCE,
        help_text="Category or purpose of the bill"
    )
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Optional remarks or notes about this bill"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Bill amount in ₹"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Current payment status"
    )
    bill_file = models.FileField(
        upload_to='bills/%Y/%m/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        help_text="Upload PDF or JPG document/bill receipt"
    )
    date_issued = models.DateField(
        auto_now_add=True,
        help_text="Date when the bill was issued"
    )

    # Simulated Dummy Payment Gateway tracking
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Simulated payment method (UPI, Card, Net Banking)"
    )
    transaction_id = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Simulated payment transaction ID"
    )
    paid_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when payment was recorded"
    )

    # Dispute tracking
    dispute_reason = models.TextField(
        blank=True,
        default='',
        help_text="Reason farmer raised for disputing this bill"
    )
    disputed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when dispute was raised"
    )
    admin_response = models.TextField(
        blank=True,
        default='',
        help_text="Admin resolution or remarks for the dispute"
    )

    objects = models.Manager()

    class Meta:
        ordering = ['-date_issued', '-id']

    def __str__(self):
        farmer_name = getattr(self.farmer, 'username', 'Unknown')
        return f"Bill #{self.pk} - {farmer_name} - {self.description} - ₹{self.amount} ({self.status})"

    @property
    def file_extension(self) -> str:
        if self.bill_file and self.bill_file.name:
            return os.path.splitext(str(self.bill_file.name))[1].lower()
        return ''

    @property
    def is_pdf(self) -> bool:
        return self.file_extension == '.pdf'

    @property
    def is_image(self) -> bool:
        return self.file_extension in ['.jpg', '.jpeg', '.png']

    @property
    def file_name(self) -> str:
        if self.bill_file and self.bill_file.name:
            return os.path.basename(str(self.bill_file.name))
        return ''

