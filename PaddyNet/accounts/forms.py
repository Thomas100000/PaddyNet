import re
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from farms.models import FarmerProfile
from millowner.models import MillOwnerProfile

User = get_user_model()

class LoginForm(forms.Form):
    username = forms.CharField(
        label="Email or Mobile Number",
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your email or mobile number',
            'required': True
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your password',
            'required': True
        })
    )

import re

class FarmerRegistrationForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your full name',
            'required': True
        }),
        label="Full Name"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create a secure password',
            'required': True
        }),
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm your password',
            'required': True
        }),
        label="Confirm Password"
    )
    village = forms.CharField(
        initial='Kainakary',
        widget=forms.TextInput(attrs={
            'class': 'form-input form-input-readonly',
            'readonly': 'readonly'
        }),
        label="Village"
    )
    farming_group = forms.CharField(
        initial='A BLOCK',
        widget=forms.TextInput(attrs={
            'class': 'form-input form-input-readonly',
            'readonly': 'readonly'
        }),
        label="Farming Group"
    )
    acres_owned = forms.DecimalField(
        min_value=0.01,
        max_digits=7,
        decimal_places=2,
        error_messages={
            'required': 'Please enter acres of paddy field owned.',
            'min_value': 'Acres owned must be greater than zero.',
            'invalid': 'Please enter a valid number of acres.'
        },
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. 2.50',
            'step': '0.01',
            'required': True
        }),
        label="Acres of Paddy Field Owned"
    )
    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. +91 98765 43210',
            'required': True
        }),
        label="Phone Number"
    )

    class Meta:
        model = User
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'yourname@example.com',
                'required': True
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError("The given email is already in use.")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            from accounts.backends import normalize_phone
            clean_digits = normalize_phone(phone_number)
            farmer_exists = FarmerProfile.objects.filter(phone_number__iexact=phone_number).exists()
            millowner_exists = MillOwnerProfile.objects.filter(phone_number__iexact=phone_number).exists()
            if not farmer_exists and not millowner_exists and clean_digits:
                for fp in FarmerProfile.objects.all():
                    if normalize_phone(fp.phone_number) == clean_digits:
                        farmer_exists = True
                        break
                if not farmer_exists:
                    for mp in MillOwnerProfile.objects.all():
                        if normalize_phone(mp.phone_number) == clean_digits:
                            millowner_exists = True
                            break

            if farmer_exists or millowner_exists:
                raise ValidationError("The given mobile number is already in use.")
        return phone_number

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")

        raw_email = self.data.get('email')
        email = (raw_email if isinstance(raw_email, str) else (raw_email[0] if isinstance(raw_email, list) and raw_email else '') or '').strip()
        raw_phone = self.data.get('phone_number')
        phone_number = (raw_phone if isinstance(raw_phone, str) else (raw_phone[0] if isinstance(raw_phone, list) and raw_phone else '') or '').strip()

        email_taken = False
        if email and User.objects.filter(email__iexact=email).exists():
            email_taken = True

        phone_taken = False
        if phone_number:
            from accounts.backends import normalize_phone
            clean_digits = normalize_phone(phone_number)
            if FarmerProfile.objects.filter(phone_number__iexact=phone_number).exists() or MillOwnerProfile.objects.filter(phone_number__iexact=phone_number).exists():
                phone_taken = True
            elif clean_digits:
                for fp in FarmerProfile.objects.all():
                    if normalize_phone(fp.phone_number) == clean_digits:
                        phone_taken = True
                        break
                if not phone_taken:
                    for mp in MillOwnerProfile.objects.all():
                        if normalize_phone(mp.phone_number) == clean_digits:
                            phone_taken = True
                            break

        if email_taken and phone_taken:
            # Clear individual field errors so single combined message is shown clearly
            if self._errors is not None:
                if 'email' in self._errors:
                    del self._errors['email']
                if 'phone_number' in self._errors:
                    del self._errors['phone_number']
            raise ValidationError("The given email and mobile number is already in use.")

        # Always enforce Kainakary and A BLOCK
        cleaned_data['village'] = 'Kainakary'
        cleaned_data['farming_group'] = 'A BLOCK'

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data['full_name']
        user.first_name = full_name
        
        # Auto-generate a unique username based on full name or email
        base_username = re.sub(r'[^a-zA-Z0-9_]', '', full_name.lower().replace(' ', '_'))
        if not base_username:
            base_username = self.cleaned_data['email'].split('@')[0]
        username = base_username
        counter = 1
        while User.objects.filter(username__iexact=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
            
        user.username = username
        user.set_password(self.cleaned_data['password'])
        user.role = User.Role.FARMER
        if commit:
            user.save()
            FarmerProfile.objects.create(
                user=user,
                full_name=full_name,
                village='Kainakary',
                phone_number=self.cleaned_data['phone_number'],
                acres_owned=self.cleaned_data['acres_owned'],
                farming_group='A BLOCK',
                is_verified=False
            )
        return user



class MillOwnerRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create a secure password',
            'required': True
        }),
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm your password',
            'required': True
        }),
        label="Confirm Password"
    )
    mill_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. Swasthik Rice Mill',
            'required': True
        }),
        label="Rice Mill Name"
    )
    mill_location = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. Ambalappuzha, Alappuzha',
            'required': True
        }),
        label="Mill Location"
    )
    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. +91 98765 43210',
            'required': True
        }),
        label="Phone Number"
    )
    fssai_license_number = forms.CharField(
        max_length=14,
        min_length=14,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter 14-digit FSSAI License Number',
            'required': True,
            'maxlength': '14',
            'pattern': r'\d{14}',
        }),
        label="FSSAI License Number"
    )

    class Meta:
        model = User
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'millowner@example.com',
                'required': True
            }),
        }

    def clean_fssai_license_number(self):
        fssai = self.cleaned_data.get('fssai_license_number', '').strip()
        if not fssai.isdigit() or len(fssai) != 14:
            raise ValidationError("FSSAI License Number must be exactly 14 digits.")
        if MillOwnerProfile.objects.filter(fssai_license_number=fssai).exists():
            raise ValidationError("The given FSSAI license number is already registered.")
        return fssai

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError("The given email is already registered.")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            from accounts.backends import normalize_phone
            clean_digits = normalize_phone(phone_number)
            farmer_exists = FarmerProfile.objects.filter(phone_number__iexact=phone_number).exists()
            millowner_exists = MillOwnerProfile.objects.filter(phone_number__iexact=phone_number).exists()
            if not farmer_exists and not millowner_exists and clean_digits:
                for fp in FarmerProfile.objects.all():
                    if normalize_phone(fp.phone_number) == clean_digits:
                        farmer_exists = True
                        break
                if not farmer_exists:
                    for mp in MillOwnerProfile.objects.all():
                        if normalize_phone(mp.phone_number) == clean_digits:
                            millowner_exists = True
                            break
            if farmer_exists or millowner_exists:
                raise ValidationError("The given mobile number is already registered.")
        return phone_number

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")

        # Combined duplicate check using raw submitted data
        raw_email = self.data.get('email')
        email = (raw_email if isinstance(raw_email, str) else (raw_email[0] if isinstance(raw_email, list) and raw_email else '') or '').strip()
        raw_phone = self.data.get('phone_number')
        phone_number = (raw_phone if isinstance(raw_phone, str) else (raw_phone[0] if isinstance(raw_phone, list) and raw_phone else '') or '').strip()
        raw_fssai = self.data.get('fssai_license_number')
        fssai = (raw_fssai if isinstance(raw_fssai, str) else (raw_fssai[0] if isinstance(raw_fssai, list) and raw_fssai else '') or '').strip()

        email_taken = bool(email and User.objects.filter(email__iexact=email).exists())

        phone_taken = False
        if phone_number:
            from accounts.backends import normalize_phone
            clean_digits = normalize_phone(phone_number)
            if (FarmerProfile.objects.filter(phone_number__iexact=phone_number).exists() or
                    MillOwnerProfile.objects.filter(phone_number__iexact=phone_number).exists()):
                phone_taken = True
            elif clean_digits:
                for fp in FarmerProfile.objects.all():
                    if normalize_phone(fp.phone_number) == clean_digits:
                        phone_taken = True
                        break
                if not phone_taken:
                    for mp in MillOwnerProfile.objects.all():
                        if normalize_phone(mp.phone_number) == clean_digits:
                            phone_taken = True
                            break

        fssai_taken = bool(fssai and MillOwnerProfile.objects.filter(fssai_license_number=fssai).exists())

        duplicates = []
        if fssai_taken:
            duplicates.append("FSSAI license number")
        if email_taken:
            duplicates.append("email")
        if phone_taken:
            duplicates.append("mobile number")

        if len(duplicates) > 1:
            # Combined message — clear individual errors for a cleaner display
            if self._errors is not None:
                for field in ('fssai_license_number', 'email', 'phone_number'):
                    if field in self._errors:
                        del self._errors[field]
            raise ValidationError(
                f"The given {' and '.join(duplicates)} is already registered."
            )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        mill_name = self.cleaned_data.get('mill_name', '')
        fssai = self.cleaned_data.get('fssai_license_number', '')

        # Auto-generate unique username from FSSAI number + mill name
        base_username = re.sub(r'[^a-zA-Z0-9_]', '', mill_name.lower().replace(' ', '_'))
        if not base_username:
            base_username = fssai
        username = base_username
        counter = 1
        while User.objects.filter(username__iexact=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user.username = username
        user.set_password(self.cleaned_data['password'])
        user.role = User.Role.MILLOWNER
        if commit:
            user.save()
            MillOwnerProfile.objects.create(
                user=user,
                mill_name=mill_name,
                mill_location=self.cleaned_data['mill_location'],
                phone_number=self.cleaned_data['phone_number'],
                fssai_license_number=fssai,
                is_verified=False,
            )
        return user
