import re
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from farms.models import FarmerProfile
from millowner.models import MillOwnerProfile

User = get_user_model()


def normalize_phone(phone_str):
    """Strip all non-digit characters from a phone number string."""
    if not phone_str:
        return ''
    return re.sub(r'\D', '', str(phone_str))


class EmailOrMobileBackend(ModelBackend):
    """
    Custom authentication backend allowing users to log in using:
    - Email address
    - FSSAI License Number (MillOwnerProfile)
    - Mobile / Phone number (FarmerProfile or MillOwnerProfile)
    - Username (fallback)
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        login_input = username.strip()
        user = None

        # 1. Try matching Email
        if '@' in login_input:
            user = User.objects.filter(email__iexact=login_input).first()

        # 2. Try matching FSSAI license number (14 digit all-numeric)
        if not user and login_input.isdigit() and len(login_input) == 14:
            millowner = MillOwnerProfile.objects.filter(fssai_license_number=login_input).first()
            if millowner:
                user = millowner.user

        # 3. Try exact phone number match in FarmerProfile or MillOwnerProfile
        if not user:
            farmer = FarmerProfile.objects.filter(phone_number__iexact=login_input).first()
            if farmer:
                user = farmer.user
            else:
                millowner = MillOwnerProfile.objects.filter(phone_number__iexact=login_input).first()
                if millowner:
                    user = millowner.user

        # 4. Try matching normalized digits against profile phone numbers
        if not user:
            input_digits = normalize_phone(login_input)
            if len(input_digits) >= 7:
                for fp in FarmerProfile.objects.all():
                    fp_digits = normalize_phone(fp.phone_number)
                    if fp_digits and (fp_digits == input_digits or fp_digits.endswith(input_digits) or input_digits.endswith(fp_digits)):
                        user = fp.user
                        break

                if not user:
                    for mp in MillOwnerProfile.objects.all():
                        mp_digits = normalize_phone(mp.phone_number)
                        if mp_digits and (mp_digits == input_digits or mp_digits.endswith(input_digits) or input_digits.endswith(mp_digits)):
                            user = mp.user
                            break

        # 5. Fallback: Email lookup without @, or Username match
        if not user:
            user = User.objects.filter(email__iexact=login_input).first()

        if not user:
            user = User.objects.filter(username__iexact=login_input).first()

        # Validate password and user active status
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
