from typing import Any
from decimal import Decimal
from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from farms.models import FarmerProfile, Field, FarmingActivity
from farms.forms import FieldForm, FarmingActivityForm

class FarmModelsAndViewsTest(TestCase):
    client: Any

    def setUp(self):
        self.client = Client()
        # Create Farmer 1
        self.farmer1 = User.objects.create_user(
            username='farmer_one',
            email='farmer1@example.com',
            password='testpassword123',
            role=User.Role.FARMER,
            first_name='Raman'
        )
        self.profile1 = FarmerProfile.objects.create(
            user=self.farmer1,
            full_name='Raman Nair',
            village='Kainakary',
            phone_number='9876543210',
            acres_owned=Decimal('5.50'),
            farming_group='A BLOCK',
            farmer_id='PDN001',
            is_verified=True
        )

        # Create Farmer 2 (for data scoping tests)
        self.farmer2 = User.objects.create_user(
            username='farmer_two',
            email='farmer2@example.com',
            password='testpassword123',
            role=User.Role.FARMER,
            first_name='Gopal'
        )
        self.profile2 = FarmerProfile.objects.create(
            user=self.farmer2,
            full_name='Gopal Pillai',
            village='Champakulam',
            phone_number='9876543211',
            acres_owned=Decimal('3.00'),
            farming_group='B BLOCK',
            farmer_id='PDN002',
            is_verified=True
        )

        # Create Mill Owner (role test)
        self.millowner = User.objects.create_user(
            username='mill_owner',
            email='mill@example.com',
            password='testpassword123',
            role=User.Role.MILLOWNER
        )

        # Create Field for Farmer 1
        self.field1 = Field.objects.create(
            owner=self.farmer1,
            field_name='North Polder Plot A',
            location='Kainakary Ward 2',
            extent_area=Decimal('2.50'),
            field_identifier='SY-101/A'
        )

        # Create Field for Farmer 2
        self.field2 = Field.objects.create(
            owner=self.farmer2,
            field_name='South Canal Field',
            location='Champakulam Ward 5',
            extent_area=Decimal('3.00'),
            field_identifier='SY-202/B'
        )

    def test_field_and_activity_models(self):
        # Create activities for field1
        act1 = FarmingActivity.objects.create(
            field=self.field1,
            activity_type=FarmingActivity.ActivityType.SOWING,
            activity_date=date(2025, 6, 1),
            season_year='2025 Kharif',
            notes='Direct sowing of Uma paddy seeds'
        )
        act2 = FarmingActivity.objects.create(
            field=self.field1,
            activity_type=FarmingActivity.ActivityType.FERTILIZER,
            activity_date=date(2025, 7, 10),
            season_year='2025 Kharif',
            notes='Applied 50kg potash and organic compost'
        )
        act3 = FarmingActivity.objects.create(
            field=self.field1,
            activity_type=FarmingActivity.ActivityType.HARVEST,
            activity_date=date(2025, 10, 15),
            season_year='2025 Kharif',
            yield_kg=Decimal('4250.00'),
            notes='Harvest completed with combine harvester'
        )

        self.assertEqual(self.field1.activities.count(), 3)
        self.assertEqual(self.field1.total_harvest_yield, Decimal('4250.00'))
        self.assertIn('North Polder Plot A', str(self.field1))
        self.assertIn('Harvest on 2025-10-15', str(act3))

    def test_form_validation(self):
        from datetime import date, timedelta

        # FieldForm validation
        invalid_field_form = FieldForm(data={
            'field_name': 'Invalid Acreage Field',
            'location': 'Kainakary',
            'extent_area': '-1.00',
            'field_identifier': 'SY-000'
        })
        self.assertFalse(invalid_field_form.is_valid())
        errors = invalid_field_form.errors or {}
        self.assertIn('extent_area', errors)

        valid_field_form = FieldForm(data={
            'field_name': 'Valid Field',
            'location': 'Kainakary',
            'extent_area': '2.00',
            'field_identifier': 'SY-999'
        })
        self.assertTrue(valid_field_form.is_valid())

        past_date   = (date.today() - timedelta(days=1)).isoformat()
        future_date = (date.today() + timedelta(days=30)).isoformat()

        # HARVEST with past date and no yield — should be INVALID
        form_past_no_yield = FarmingActivityForm(data={
            'activity_type': FarmingActivity.ActivityType.HARVEST,
            'activity_date': past_date,
            'season_year': '2025 Kharif',
            'yield_kg': '',
            'notes': 'test'
        })
        self.assertFalse(form_past_no_yield.is_valid())
        self.assertIn('yield_kg', form_past_no_yield.errors or {})

        # HARVEST with past date and negative yield — should be INVALID
        form_past_neg_yield = FarmingActivityForm(data={
            'activity_type': FarmingActivity.ActivityType.HARVEST,
            'activity_date': past_date,
            'season_year': '2025 Kharif',
            'yield_kg': '-500',
            'notes': 'test'
        })
        self.assertFalse(form_past_neg_yield.is_valid())
        self.assertIn('yield_kg', form_past_neg_yield.errors or {})

        # HARVEST with past date and valid yield — should be VALID
        form_past_valid = FarmingActivityForm(data={
            'activity_type': FarmingActivity.ActivityType.HARVEST,
            'activity_date': past_date,
            'season_year': '2025 Kharif',
            'yield_kg': '4500',
            'notes': 'Good yield'
        })
        self.assertTrue(form_past_valid.is_valid())

        # HARVEST with future date and NO yield — should be VALID (not harvested yet)
        form_future_no_yield = FarmingActivityForm(data={
            'activity_type': FarmingActivity.ActivityType.HARVEST,
            'activity_date': future_date,
            'season_year': '2026 Kharif',
            'yield_kg': '',
            'notes': 'Planned harvest'
        })
        self.assertTrue(form_future_no_yield.is_valid())

        # HARVEST with future date and negative yield — still INVALID
        form_future_neg_yield = FarmingActivityForm(data={
            'activity_type': FarmingActivity.ActivityType.HARVEST,
            'activity_date': future_date,
            'season_year': '2026 Kharif',
            'yield_kg': '-100',
            'notes': 'Bad input'
        })
        self.assertFalse(form_future_neg_yield.is_valid())
        self.assertIn('yield_kg', form_future_neg_yield.errors or {})


    def test_access_control(self):
        # Unauthenticated access to field list should redirect to login
        response = self.client.get(reverse('field_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

        # Mill owner accessing field list should get 403 (wrong role)
        self.client.login(username='mill_owner', password='testpassword123')
        response = self.client.get(reverse('field_list'))
        self.assertEqual(response.status_code, 403)
        self.client.logout()

    def test_farmer_scoping_and_isolation(self):
        # Log in as Farmer 1
        self.client.login(username='farmer_one', password='testpassword123')

        # Farmer 1 should see field1 but NOT field2 in field_list
        response = self.client.get(reverse('field_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'North Polder Plot A')
        self.assertNotContains(response, 'South Canal Field')

        # Farmer 1 attempting to view field2 detail should get 404
        response = self.client.get(reverse('field_detail', kwargs={'field_id': self.field2.id}))
        self.assertEqual(response.status_code, 404)

        # Farmer 1 attempting to edit field2 should get 404
        response = self.client.get(reverse('field_edit', kwargs={'field_id': self.field2.id}))
        self.assertEqual(response.status_code, 404)

        # Farmer 1 attempting to delete field2 should get 404
        response = self.client.post(reverse('field_delete', kwargs={'field_id': self.field2.id}))
        self.assertEqual(response.status_code, 404)

    def test_field_crud_flow(self):
        self.client.login(username='farmer_one', password='testpassword123')

        # CREATE
        create_url = reverse('field_create')
        post_data = {
            'field_name': 'New Wetland Plot',
            'location': 'Kainakary East Ward',
            'extent_area': '1.75',
            'field_identifier': 'SY-303/C'
        }
        response = self.client.post(create_url, post_data)
        self.assertEqual(response.status_code, 302)

        new_field = Field.objects.get(field_name='New Wetland Plot')
        self.assertEqual(new_field.owner, self.farmer1)
        self.assertEqual(new_field.extent_area, Decimal('1.75'))

        # EDIT
        edit_url = reverse('field_edit', kwargs={'field_id': new_field.id})
        update_data = {
            'field_name': 'New Wetland Plot Updated',
            'location': 'Kainakary East Ward 4',
            'extent_area': '1.80',
            'field_identifier': 'SY-303/C-REV'
        }
        response = self.client.post(edit_url, update_data)
        self.assertEqual(response.status_code, 302)
        new_field.refresh_from_db()
        self.assertEqual(new_field.field_name, 'New Wetland Plot Updated')
        self.assertEqual(new_field.extent_area, Decimal('1.80'))

        # DELETE
        delete_url = reverse('field_delete', kwargs={'field_id': new_field.id})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Field.objects.filter(id=new_field.id).exists())

    def test_activity_timeline_and_logging(self):
        self.client.login(username='farmer_one', password='testpassword123')

        # Add activity via POST on field_detail
        detail_url = reverse('field_detail', kwargs={'field_id': self.field1.id})
        act_data = {
            'activity_type': 'SOWING',
            'activity_date': '2025-06-15',
            'season_year': '2025 Kharif',
            'yield_kg': '',
            'notes': 'Transplanted high-yield hybrid seedlings'
        }
        response = self.client.post(detail_url, act_data)
        self.assertEqual(response.status_code, 302)

        # Verify activity created
        act = FarmingActivity.objects.get(field=self.field1, activity_type='SOWING')
        self.assertEqual(act.season_year, '2025 Kharif')

        # Add Harvest activity with yield
        harvest_data = {
            'activity_type': 'HARVEST',
            'activity_date': '2025-10-20',
            'season_year': '2025 Kharif',
            'yield_kg': '5000',
            'notes': 'Bumper harvest'
        }
        self.client.post(detail_url, harvest_data)

        # GET detail page verifies activities in response
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Transplanted high-yield hybrid seedlings')
        self.assertContains(response, '5000')

        # Delete activity
        harvest_act = FarmingActivity.objects.get(field=self.field1, activity_type='HARVEST')
        del_url = reverse('activity_delete', kwargs={'activity_id': harvest_act.id})
        response = self.client.post(del_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(FarmingActivity.objects.filter(id=harvest_act.id).exists())

    def test_seasonal_statistics(self):
        self.client.login(username='farmer_one', password='testpassword123')

        # Log activities across two seasons for field1
        FarmingActivity.objects.create(
            field=self.field1,
            activity_type=FarmingActivity.ActivityType.SOWING,
            activity_date=date(2024, 6, 1),
            season_year='2024 Kharif'
        )
        FarmingActivity.objects.create(
            field=self.field1,
            activity_type=FarmingActivity.ActivityType.HARVEST,
            activity_date=date(2024, 10, 1),
            season_year='2024 Kharif',
            yield_kg=Decimal('3600.00')
        )
        FarmingActivity.objects.create(
            field=self.field1,
            activity_type=FarmingActivity.ActivityType.SOWING,
            activity_date=date(2025, 6, 1),
            season_year='2025 Kharif'
        )
        FarmingActivity.objects.create(
            field=self.field1,
            activity_type=FarmingActivity.ActivityType.HARVEST,
            activity_date=date(2025, 10, 1),
            season_year='2025 Kharif',
            yield_kg=Decimal('4800.00')
        )

        stats_url = reverse('field_statistics')
        response = self.client.get(stats_url)
        self.assertEqual(response.status_code, 200)

        # Check table contents
        self.assertContains(response, '2024 Kharif')
        self.assertContains(response, '3600')
        self.assertContains(response, '2025 Kharif')
        self.assertContains(response, '4800')

        # Check Chart.js JSON data presence
        self.assertContains(response, 'seasonYieldChart')
        self.assertContains(response, '3600.0')
        self.assertContains(response, '4800.0')

    def test_farmer_dashboard_integration(self):
        self.client.login(username='farmer_one', password='testpassword123')
        dashboard_url = reverse('farmer_dashboard')
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, 200)

        # Should contain links to field list, field create, and statistics
        self.assertContains(response, reverse('field_list'))
        self.assertContains(response, reverse('field_create'))
        self.assertContains(response, reverse('field_statistics'))
        self.assertContains(response, self.field1.field_name)

    def test_farmer_notifications_page(self):
        from notices.models import Notification
        admin_user = User.objects.create_user(
            username='admin_announcer',
            email='admin@kuttanad.org',
            password='AdminPassword123!',
            role=User.Role.ADMIN
        )
        notif1 = Notification.objects.create(
            title='Earlier Advisory Notice',
            message='Please prepare seeds for Kharif sowing.',
            posted_by=admin_user
        )
        notif2 = Notification.objects.create(
            title='Newest Dewatering Schedule',
            message='Pumping motors will operate from 6 AM to 6 PM.',
            posted_by=admin_user
        )

        # Unauthenticated
        res = self.client.get(reverse('farmer_notifications'))
        self.assertEqual(res.status_code, 302)

        # Non-farmer (millowner) — should get 403
        self.client.login(username='mill_owner', password='testpassword123')
        res_mo = self.client.get(reverse('farmer_notifications'))
        self.assertEqual(res_mo.status_code, 403)
        self.client.logout()

        # Farmer 1
        self.client.login(username='farmer_one', password='testpassword123')
        res_f1 = self.client.get(reverse('farmer_notifications'))
        self.assertEqual(res_f1.status_code, 200)
        self.assertContains(res_f1, 'Newest Dewatering Schedule')
        self.assertContains(res_f1, 'Earlier Advisory Notice')
        # Check ordering: newest first
        notifications_list = list(res_f1.context['notifications'])
        self.assertEqual(notifications_list[0], notif2)
        self.assertEqual(notifications_list[1], notif1)

    def test_farmer_bills_page_and_scoping(self):
        from billing.models import Bill
        # Create bills for Farmer 1
        bill_f1_pending = Bill.objects.create(
            farmer=self.farmer1,
            amount=Decimal('1500.00'),
            description='Bund Repair Surcharge',
            status=Bill.Status.PENDING
        )
        bill_f1_paid = Bill.objects.create(
            farmer=self.farmer1,
            amount=Decimal('2200.00'),
            description='Seeds Procurement',
            status=Bill.Status.PAID
        )

        # Create bill for Farmer 2
        bill_f2 = Bill.objects.create(
            farmer=self.farmer2,
            amount=Decimal('9999.00'),
            description='Confidential Secret Bill for Farmer 2',
            status=Bill.Status.PENDING
        )

        # Unauthenticated
        res = self.client.get(reverse('farmer_bills'))
        self.assertEqual(res.status_code, 302)

        # Non-farmer (millowner) — should get 403
        self.client.login(username='mill_owner', password='testpassword123')
        res_mo = self.client.get(reverse('farmer_bills'))
        self.assertEqual(res_mo.status_code, 403)
        self.client.logout()

        # Farmer 1
        self.client.login(username='farmer_one', password='testpassword123')
        res_f1 = self.client.get(reverse('farmer_bills'))
        self.assertEqual(res_f1.status_code, 200)
        self.assertContains(res_f1, 'Bund Repair Surcharge')
        self.assertContains(res_f1, 'Seeds Procurement')
        # Crucial security check: farmer 1 CANNOT see farmer 2's bill
        self.assertNotContains(res_f1, 'Confidential Secret Bill for Farmer 2')
        self.assertNotContains(res_f1, '9999.00')

        # Filter by status PENDING
        res_pending = self.client.get(reverse('farmer_bills') + '?status=PENDING')
        self.assertEqual(res_pending.status_code, 200)
        self.assertContains(res_pending, 'Bund Repair Surcharge')
        self.assertNotContains(res_pending, 'Seeds Procurement')

        # Filter by status PAID
        res_paid = self.client.get(reverse('farmer_bills') + '?status=PAID')
        self.assertEqual(res_paid.status_code, 200)
        self.assertContains(res_paid, 'Seeds Procurement')
        self.assertNotContains(res_paid, 'Bund Repair Surcharge')

    def test_farmer_bids_accept_reject_bargain(self):
        from millowner.models import Bid
        field = Field.objects.create(
            owner=self.farmer1,
            field_name='North Polder',
            location='Kainakary',
            extent_area=Decimal('10.00')
        )
        bid = Bid.objects.create(
            millowner=self.millowner,
            field=field,
            amount=Decimal('500000.00'),
            per_kg_rate=Decimal('50.00'),
            notes='Farm-gate pickup'
        )

        # 1. Login as Farmer 1 and check bids page contains action triggers
        self.client.login(username='farmer_one', password='testpassword123')
        res = self.client.get(reverse('farmer_bids'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Decision &amp; Bargain')
        self.assertContains(res, 'openBargainModal')
        self.assertContains(res, 'openAcceptModal')
        self.assertContains(res, 'openRejectModal')

        # 2. Test Bargaining / Counter-Offer
        res_bargain = self.client.post(
            reverse('farmer_respond_bid', args=[bid.id]),
            {
                'action': 'bargain',
                'counter_amount': '520000.00',
                'counter_per_kg_rate': '52.00',
                'farmer_note': 'Quality Jyothi harvest, expect 52/kg.'
            }
        )
        self.assertRedirects(res_bargain, reverse('farmer_bids'))
        bid.refresh_from_db()
        self.assertEqual(bid.status, Bid.Status.BARGAINING)
        self.assertEqual(bid.counter_amount, Decimal('520000.00'))
        self.assertEqual(bid.counter_per_kg_rate, Decimal('52.00'))
        self.assertEqual(bid.farmer_note, 'Quality Jyothi harvest, expect 52/kg.')

        # 3. Test Accept
        res_accept = self.client.post(
            reverse('farmer_respond_bid', args=[bid.id]),
            {
                'action': 'accept',
                'farmer_note': 'Accepted. Transport ready.'
            }
        )
        self.assertRedirects(res_accept, reverse('farmer_bids'))
        bid.refresh_from_db()
        self.assertEqual(bid.status, Bid.Status.ACCEPTED)
        self.assertEqual(bid.farmer_note, 'Accepted. Transport ready.')

        # 4. Test Reset
        res_reset = self.client.post(
            reverse('farmer_respond_bid', args=[bid.id]),
            {'action': 'reset'}
        )
        self.assertRedirects(res_reset, reverse('farmer_bids'))
        bid.refresh_from_db()
        self.assertEqual(bid.status, Bid.Status.PENDING)

        # 5. Test Reject
        res_reject = self.client.post(
            reverse('farmer_respond_bid', args=[bid.id]),
            {
                'action': 'reject',
                'farmer_note': 'Offer too low.'
            }
        )
        self.assertRedirects(res_reject, reverse('farmer_bids'))
        bid.refresh_from_db()
        self.assertEqual(bid.status, Bid.Status.REJECTED)
        self.assertEqual(bid.farmer_note, 'Offer too low.')

        # 6. Unauthorized farmer (Farmer 2) cannot respond to Farmer 1's bid
        self.client.logout()
        self.client.login(username='farmer_two', password='testpassword123')
        res_unauth = self.client.post(
            reverse('farmer_respond_bid', args=[bid.id]),
            {'action': 'accept'}
        )
        self.assertRedirects(res_unauth, reverse('farmer_bids'))
        bid.refresh_from_db()
        # Status should NOT change to ACCEPTED because farmer_two has no permission
        self.assertEqual(bid.status, Bid.Status.REJECTED)

    def test_farmer_pay_bill_dummy_gateway(self):
        from billing.models import Bill
        bill = Bill.objects.create(
            farmer=self.farmer1,
            amount=Decimal('3500.00'),
            description='Tractor Bill',
            status=Bill.Status.PENDING
        )

        # GET payment portal
        self.client.login(username='farmer_one', password='testpassword123')
        res_get = self.client.get(reverse('farmer_pay_bill', args=[bill.id]))
        self.assertEqual(res_get.status_code, 200)
        self.assertContains(res_get, '3500.00')
        self.assertContains(res_get, 'Tractor Bill')

        # POST simulated payment
        res_pay = self.client.post(
            reverse('farmer_pay_bill', args=[bill.id]),
            {'payment_method': 'UPI (PhonePe - farmer@ybl)'}
        )
        self.assertRedirects(res_pay, reverse('farmer_bills'))
        bill.refresh_from_db()
        self.assertEqual(bill.status, Bill.Status.PAID)
        self.assertEqual(bill.payment_method, 'UPI (PhonePe - farmer@ybl)')
        self.assertTrue(bill.transaction_id.startswith('TXN-PDN-'))
        self.assertIsNotNone(bill.paid_at)

        # Farmer 2 cannot pay or access Farmer 1's bill
        self.client.logout()
        self.client.login(username='farmer_two', password='testpassword123')
        res_unauth_pay = self.client.post(
            reverse('farmer_pay_bill', args=[bill.id]),
            {'payment_method': 'UPI'}
        )
        self.assertEqual(res_unauth_pay.status_code, 404)

    def test_farmer_raise_dispute(self):
        from billing.models import Bill
        bill = Bill.objects.create(
            farmer=self.farmer1,
            amount=Decimal('1850.00'),
            description='Harvester Bill',
            status=Bill.Status.PENDING
        )

        self.client.login(username='farmer_one', password='testpassword123')

        # POST dispute
        res_dispute = self.client.post(
            reverse('farmer_raise_dispute', args=[bill.id]),
            {
                'dispute_type': 'Incorrect operational hours / rate',
                'dispute_details': 'Harvester was used for only 1.5 hours instead of 3 hours billed.'
            }
        )
        self.assertRedirects(res_dispute, reverse('farmer_bills'))
        bill.refresh_from_db()
        self.assertEqual(bill.status, Bill.Status.DISPUTED)
        self.assertIn('Harvester was used for only 1.5 hours', bill.dispute_reason)
        self.assertIsNotNone(bill.disputed_at)

        # GET bills page shows disputed filter and amount
        res_page = self.client.get(reverse('farmer_bills') + '?status=DISPUTED')
        self.assertEqual(res_page.status_code, 200)
        self.assertContains(res_page, '1850.00')
        self.assertContains(res_page, 'Disputed')
