from typing import Any
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from farms.models import FarmerProfile, Field, FarmingActivity
from millowner.models import MillOwnerProfile, Bid
from millowner.forms import BidForm

User = get_user_model()

class MillOwnerBiddingTestCase(TestCase):
    def setUp(self):
        self.client: Any = Client()

        # Create Farmer
        self.farmer_user = User.objects.create_user(
            username='farmer_shaji',
            email='shaji@example.com',
            password='Password123!',
            role=User.Role.FARMER,
            first_name='Shaji'
        )
        self.farmer_profile = FarmerProfile.objects.create(
            user=self.farmer_user,
            full_name='Shaji P.',
            village='Kainakary',
            phone_number='9876543210',
            acres_owned=4.5,
            farming_group='A BLOCK',
            is_verified=True
        )

        # Create 2 Fields for Farmer: 1 harvested, 1 unharvested
        self.harvested_field = Field.objects.create(
            owner=self.farmer_user,
            field_name='North Polder Parcel 1',
            location='Kainakary North',
            extent_area=3.0,
            field_identifier='SY-101/A'
        )
        self.harvest_activity = FarmingActivity.objects.create(
            field=self.harvested_field,
            activity_type=FarmingActivity.ActivityType.HARVEST,
            activity_date='2025-10-15',
            season_year='2025 Kharif',
            yield_kg=4500.0,
            notes='High quality Uma paddy harvested.'
        )

        self.unharvested_field = Field.objects.create(
            owner=self.farmer_user,
            field_name='South Polder Parcel 2',
            location='Kainakary South',
            extent_area=2.0,
            field_identifier='SY-102/B'
        )
        self.sowing_activity = FarmingActivity.objects.create(
            field=self.unharvested_field,
            activity_type=FarmingActivity.ActivityType.SOWING,
            activity_date='2025-11-01',
            season_year='2025 Rabi',
            notes='Seeds sown recently.'
        )

        # Create Mill Owner 1
        self.millowner_user1 = User.objects.create_user(
            username='swasthik_mill',
            email='swasthik@example.com',
            password='Password123!',
            role=User.Role.MILLOWNER,
            first_name='Swasthik'
        )
        self.millowner_profile1 = MillOwnerProfile.objects.create(
            user=self.millowner_user1,
            mill_name='Swasthik Modern Rice Mill',
            mill_location='Ambalappuzha',
            phone_number='9123456780',
            fssai_license_number='12345678901234',
            is_verified=True
        )

        # Create Mill Owner 2
        self.millowner_user2 = User.objects.create_user(
            username='kerala_rice_mill',
            email='keralarice@example.com',
            password='Password123!',
            role=User.Role.MILLOWNER,
            first_name='Kerala Mills'
        )
        self.millowner_profile2 = MillOwnerProfile.objects.create(
            user=self.millowner_user2,
            mill_name='Kerala Agro Foods Mill',
            mill_location='Alappuzha Town',
            phone_number='9876501234',
            fssai_license_number='98765432109876',
            is_verified=True
        )

    def test_bid_model_creation_and_ordering(self):
        bid1 = Bid.objects.create(
            millowner=self.millowner_user1,
            field=self.harvested_field,
            amount=55000.00,
            notes='Payment within 2 days of delivery'
        )
        bid2 = Bid.objects.create(
            millowner=self.millowner_user2,
            field=self.harvested_field,
            amount=60000.00,
            notes='Farm-gate pickup included'
        )
        self.assertEqual(Bid.objects.count(), 2)
        self.assertIn("Bid ₹60000.0 on North Polder Parcel 1", str(bid2))
        
        # Test default ordering (-date)
        all_bids = list(Bid.objects.all())
        self.assertEqual(all_bids[0], bid2)
        self.assertEqual(all_bids[1], bid1)

    def test_bid_form_validation(self):
        valid_form = BidForm(data={'amount': '52000.50', 'notes': 'Test notes'})
        self.assertTrue(valid_form.is_valid())

        invalid_form = BidForm(data={'amount': '-100', 'notes': 'Negative amount'})
        self.assertFalse(invalid_form.is_valid())
        errors = invalid_form.errors or {}
        self.assertIn('amount', errors)

        zero_form = BidForm(data={'amount': '0', 'notes': 'Zero amount'})
        self.assertFalse(zero_form.is_valid())

    def test_millowner_access_control(self):
        # Unauthenticated access redirects to login
        response: Any = self.client.get(reverse('millowner_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

        # Farmer accessing mill owner dashboard gets 403 (wrong role)
        self.client.login(username='farmer_shaji', password='Password123!')
        response = self.client.get(reverse('millowner_dashboard'))
        self.assertEqual(response.status_code, 403)
        self.client.logout()

        # Mill owner accessing dashboard gets 200 OK
        self.client.login(username='swasthik_mill', password='Password123!')
        response = self.client.get(reverse('millowner_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Swasthik Modern Rice Mill")

    def test_millowner_field_browse_scoping(self):
        self.client.login(username='swasthik_mill', password='Password123!')
        response: Any = self.client.get(reverse('millowner_field_browse'))
        self.assertEqual(response.status_code, 200)
        
        # Harvested field should appear
        self.assertContains(response, "North Polder Parcel 1")
        self.assertContains(response, "4500")
        
        # Unharvested field should NOT appear in browse list
        self.assertNotContains(response, "South Polder Parcel 2")

    def test_millowner_place_bid_flow(self):
        self.client.login(username='swasthik_mill', password='Password123!')
        
        # GET field detail
        response: Any = self.client.get(reverse('millowner_field_detail', kwargs={'field_id': self.harvested_field.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "North Polder Parcel 1")
        self.assertContains(response, "Submit Purchase Bid")

        # POST valid bid
        post_response: Any = self.client.post(
            reverse('millowner_field_detail', kwargs={'field_id': self.harvested_field.id}),
            {
                'amount': '58000.00',
                'notes': 'Spot cash settlement on loading'
            }
        )
        self.assertEqual(post_response.status_code, 302)
        self.assertEqual(Bid.objects.filter(millowner=self.millowner_user1, field=self.harvested_field).count(), 1)

        # Check bid history page
        history_resp: Any = self.client.get(reverse('millowner_bid_history'))
        self.assertEqual(history_resp.status_code, 200)
        self.assertContains(history_resp, "58000.00")
        self.assertContains(history_resp, "North Polder Parcel 1")

    def test_farmer_side_bids_view_sorted_by_amount_descending(self):
        # Create multiple bids on the farmer's harvested field
        Bid.objects.create(
            millowner=self.millowner_user1,
            field=self.harvested_field,
            amount=50000.00,
            notes='First bid'
        )
        Bid.objects.create(
            millowner=self.millowner_user2,
            field=self.harvested_field,
            amount=65000.00,
            notes='Higher competing bid'
        )

        # Log in as Farmer
        self.client.login(username='farmer_shaji', password='Password123!')
        response: Any = self.client.get(reverse('farmer_bids'))
        self.assertEqual(response.status_code, 200)

        # Content assertions
        self.assertContains(response, "Mill Owner Bids on Your Harvests")
        self.assertContains(response, "Kerala Agro Foods Mill")
        self.assertContains(response, "Swasthik Modern Rice Mill")
        self.assertContains(response, "65000.00")
        self.assertContains(response, "50000.00")

        # Verify higher bid appears before lower bid in context
        fields_with_bids = response.context['fields_with_bids']
        self.assertTrue(len(fields_with_bids) >= 1)
        for item in fields_with_bids:
            if item['field'] == self.harvested_field:
                bids_list = list(item['bids'])
                self.assertEqual(len(bids_list), 2)
                self.assertEqual(bids_list[0].amount, 65000.00)
                self.assertEqual(bids_list[1].amount, 50000.00)
