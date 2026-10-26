from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model, authenticate
from farms.models import FarmerProfile
from millowner.models import MillOwnerProfile

User = get_user_model()

class EmailOrMobileAuthenticationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a Farmer user
        self.farmer_user = User.objects.create_user(
            username='farmer_joe',
            email='farmer.joe@example.com',
            password='Password123!',
            role=User.Role.FARMER,
            first_name='Farmer Joe'
        )
        self.farmer_profile = FarmerProfile.objects.create(
            user=self.farmer_user,
            full_name='Farmer Joe',
            village='Kainakary',
            phone_number='+91 98765 43210',
            acres_owned=5.00,
            farming_group='A BLOCK',
            is_verified=True
        )

        # Create a Mill Owner user
        self.millowner_user = User.objects.create_user(
            username='mill_owner_bob',
            email='bob@swasthikmills.com',
            password='Password123!',
            role=User.Role.MILLOWNER,
            first_name='Bob'
        )
        self.millowner_profile = MillOwnerProfile.objects.create(
            user=self.millowner_user,
            mill_name='Swasthik Rice Mill',
            mill_location='Ambalappuzha',
            phone_number='+91 91234 56789'
        )

    def test_authenticate_with_email(self):
        user = authenticate(username='farmer.joe@example.com', password='Password123!')
        self.assertEqual(user, self.farmer_user)

    def test_authenticate_with_phone_number_exact(self):
        user = authenticate(username='+91 98765 43210', password='Password123!')
        self.assertEqual(user, self.farmer_user)

    def test_authenticate_with_phone_number_digits_only(self):
        user = authenticate(username='9876543210', password='Password123!')
        self.assertEqual(user, self.farmer_user)

    def test_authenticate_millowner_with_phone(self):
        user = authenticate(username='9123456789', password='Password123!')
        self.assertEqual(user, self.millowner_user)

    def test_authenticate_with_username_fallback(self):
        user = authenticate(username='farmer_joe', password='Password123!')
        self.assertEqual(user, self.farmer_user)

    def test_authenticate_wrong_password(self):
        user = authenticate(username='farmer.joe@example.com', password='wrongpassword')
        self.assertIsNone(user)

    def test_login_view_with_email(self):
        response = self.client.post(reverse('login'), {
            'username': 'farmer.joe@example.com',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('farmer_dashboard'))

    def test_login_view_with_mobile(self):
        response = self.client.post(reverse('login'), {
            'username': '9876543210',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('farmer_dashboard'))


class FarmerRegistrationDuplicateValidationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.existing_user = User.objects.create_user(
            username='existing_farmer',
            email='existing@example.com',
            password='Password123!',
            role=User.Role.FARMER
        )
        self.existing_profile = FarmerProfile.objects.create(
            user=self.existing_user,
            full_name='Existing Farmer',
            village='Kainakary',
            phone_number='9876543210',
            acres_owned=3.5,
            farming_group='A BLOCK',
            is_verified=True
        )

    def test_register_duplicate_email(self):
        response = self.client.post(reverse('register_farmer'), {
            'full_name': 'New Farmer',
            'email': 'existing@example.com',
            'phone_number': '9999988888',
            'acres_owned': '2.0',
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The given email is already in use.")

    def test_register_duplicate_mobile(self):
        response = self.client.post(reverse('register_farmer'), {
            'full_name': 'New Farmer',
            'email': 'newfarmer@example.com',
            'phone_number': '9876543210',
            'acres_owned': '2.0',
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The given mobile number is already in use.")

    def test_register_duplicate_email_and_mobile(self):
        response = self.client.post(reverse('register_farmer'), {
            'full_name': 'New Farmer',
            'email': 'existing@example.com',
            'phone_number': '9876543210',
            'acres_owned': '2.0',
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The given email and mobile number is already in use.")

