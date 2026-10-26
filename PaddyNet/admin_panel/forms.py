import os
from django import forms
from django.contrib.auth import get_user_model
from billing.models import Bill
from notices.models import Notification

User = get_user_model()

class FarmerModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        if hasattr(obj, 'farmer_profile') and obj.farmer_profile.full_name:
            farmer_id_str = f"[{obj.farmer_profile.farmer_id}] " if obj.farmer_profile.farmer_id else ""
            return f"{farmer_id_str}{obj.farmer_profile.full_name} ({obj.farmer_profile.village}) - {obj.username}"
        return f"{obj.username} ({obj.email})"


class BillForm(forms.ModelForm):
    BILL_CATEGORY_CHOICES = [
        ('Bund Maintenance', 'Bund Maintenance'),
        ('Tractor Bill', 'Tractor Bill'),
        ('Seeds Bill', 'Seeds Bill'),
        ('Harvester Bill', 'Harvester Bill'),
        ('Water Pumping', 'Water Pumping'),
        ('Fertilizer Bill', 'Fertilizer Bill'),
        ('Pesticides Bill', 'Pesticides Bill'),
        ('Drainage & Dewatering Charges', 'Drainage & Dewatering Charges'),
        ('Polder Pumping Electricity Bill', 'Polder Pumping Electricity Bill'),
        ('Other Charges', 'Other Charges'),
    ]

    farmer = FarmerModelChoiceField(
        queryset=User.objects.filter(
            role=User.Role.FARMER,
            is_staff=False,
            is_superuser=False,
            farmer_profile__isnull=False
        ).select_related('farmer_profile'),
        empty_label="-- Select Farmer --",
        widget=forms.Select(attrs={'class': 'form-input'}),
        help_text="Select the farmer to issue this bill to."
    )

    description = forms.ChoiceField(
        choices=BILL_CATEGORY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-input'}),
        label="Bill Category *"
    )

    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        error_messages={
            'required': 'Please enter the bill amount.',
            'min_value': 'Bill amount must be greater than zero.',
            'invalid': 'Please enter a valid bill amount.'
        },
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '0.01',
            'min': '0.01',
            'placeholder': 'Enter bill amount in ₹ (e.g. 2500.00)'
        }),
        label="Amount (₹) *"
    )

    bill_file = forms.FileField(
        required=False,
        label="Bill Document / Receipt (PDF or JPG)",
        widget=forms.FileInput(attrs={
            'id': 'id_bill_file',
            'class': 'form-input',
            'accept': '.pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png'
        }),
        help_text="Attach a PDF or JPG copy of the bill/voucher (Max: 10MB)."
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 2,
            'placeholder': 'Optional remarks, voucher number, or plot references...'
        }),
        label="Additional Remarks / Notes"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['farmer'].queryset = User.objects.filter(
            role=User.Role.FARMER,
            is_staff=False,
            is_superuser=False,
            farmer_profile__isnull=False
        ).select_related('farmer_profile').order_by('farmer_profile__full_name', 'username')

    class Meta:
        model = Bill
        fields = ['farmer', 'description', 'amount', 'bill_file', 'notes']
        error_messages = {
            'farmer': {
                'required': 'Please select a farmer for this bill.',
            }
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Bill amount must be greater than zero.")
        return amount

    def clean_bill_file(self):
        file = self.cleaned_data.get('bill_file')
        if file:
            valid_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError("Only PDF and image files (.jpg, .jpeg, .png) are permitted.")
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Bill file size cannot exceed 10MB.")
        return file


class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['title', 'message']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. Monsoon Season Advisory & Dewatering Schedule'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 5,
                'placeholder': 'Type announcement message details for the farming community...'
            }),
        }
        error_messages = {
            'title': {
                'required': 'Please provide a title for the announcement.',
            },
            'message': {
                'required': 'Please enter the notification message body.',
            }
        }
