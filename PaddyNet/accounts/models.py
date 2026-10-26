from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        FARMER = 'FARMER', 'Farmer'
        ADMIN = 'ADMIN', 'Admin'
        MILLOWNER = 'MILLOWNER', 'Mill Owner'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.FARMER,
        help_text="Role of the user in the PaddyNet ecosystem"
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
