import os
from typing import Any
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from farms.models import FarmerProfile, Field
from millowner.models import MillOwnerProfile
from django.core.files.uploadedfile import SimpleUploadedFile
from billing.models import Bill
from notices.models import Notification

User = get_user_model()

class AdminVerificationAndRejectionTestCase(TestCase):
    client: Any

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin_user',
            email='admin@paddynet.com',
            password='AdminPassword123!',
            role=User.Role.ADMIN
        )

        self.farmer_user1 = User.objects.create_user(
            username='farmer1',
            email='farmer1@example.com',
            password='Password123!',
            role=User.Role.FARMER
        )
        self.farmer_profile1 = FarmerProfile.objects.create(
            user=self.farmer_user1,
            full_name='Farmer One',
            phone_number='9876543211',
            is_verified=False
        )

        self.farmer_user2 = User.objects.create_user(
            username='farmer2',
            email='farmer2@example.com',
            password='Password123!',
            role=User.Role.FARMER
        )
        self.farmer_profile2 = FarmerProfile.objects.create(
            user=self.farmer_user2,
            full_name='Farmer Two',
            phone_number='9876543212',
            is_verified=False
        )

    def test_verify_farmer_generates_pdn_id(self):
        self.client.login(username='admin_user', password='AdminPassword123!')
        
        # Verify first farmer -> PDN1001
        res1 = self.client.post(reverse('verify_farmer', args=[self.farmer_profile1.id]))
        self.assertEqual(res1.status_code, 302)
        self.farmer_profile1.refresh_from_db()
        self.assertTrue(self.farmer_profile1.is_verified)
        self.assertEqual(self.farmer_profile1.farmer_id, 'PDN1001')

        # Verify second farmer -> PDN1002
        res2 = self.client.post(reverse('verify_farmer', args=[self.farmer_profile2.id]))
        self.assertEqual(res2.status_code, 302)
        self.farmer_profile2.refresh_from_db()
        self.assertTrue(self.farmer_profile2.is_verified)
        self.assertEqual(self.farmer_profile2.farmer_id, 'PDN1002')

    def test_reject_farmer_registration(self):
        self.client.login(username='admin_user', password='AdminPassword123!')
        
        res = self.client.post(reverse('reject_farmer', args=[self.farmer_profile1.id]))
        self.assertEqual(res.status_code, 302)
        
        self.assertFalse(FarmerProfile.objects.filter(id=self.farmer_profile1.id).exists())
        self.assertFalse(User.objects.filter(id=self.farmer_user1.id).exists())


class AdminPanelAppFeaturesTestCase(TestCase):
    client: Any

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='superadmin',
            email='admin@kuttanad.org',
            password='Password123!',
            role=User.Role.ADMIN
        )
        self.farmer_user = User.objects.create_user(
            username='ramankutty',
            email='raman@example.com',
            password='Password123!',
            role=User.Role.FARMER
        )
        self.farmer_profile = FarmerProfile.objects.create(
            user=self.farmer_user,
            full_name='Raman Kutty',
            village='Kainakary',
            phone_number='9447123456',
            acres_owned=4.50,
            farming_group='A BLOCK',
            farmer_id='PDN1005',
            is_verified=True
        )

        self.millowner_user = User.objects.create_user(
            username='millcorp',
            email='mill@example.com',
            password='Password123!',
            role=User.Role.MILLOWNER
        )
        self.millowner_profile = MillOwnerProfile.objects.create(
            user=self.millowner_user,
            mill_name='Kuttanad Modern Agro Mill',
            fssai_license_number='FSSAI-88392019',
            phone_number='9846012345',
            mill_location='Alappuzha Polder Road',
            is_verified=True
        )

        self.field1 = Field.objects.create(
            owner=self.farmer_user,
            field_name='North Polder Parcel 1',
            location='Kainakary Ward 4',
            extent_area=2.50,
            field_identifier='SY-104/A'
        )
        self.field2 = Field.objects.create(
            owner=self.farmer_user,
            field_name='East Canal Plot',
            location='Kainakary Block B',
            extent_area=2.00,
            field_identifier='SY-105/C'
        )

    def test_permission_protection(self):
        # Unauthenticated access redirects to login
        res = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(res.status_code, 302)
        self.assertIn('/accounts/login/', res.url)

        # Farmer accessing admin dashboard gets 403 Forbidden
        self.client.login(username='ramankutty', password='Password123!')
        res_farmer = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(res_farmer.status_code, 403)
        self.client.logout()

    def test_admin_dashboard_metrics_and_notifications(self):
        self.client.login(username='superadmin', password='Password123!')

        # Create a pending bill and a paid bill
        Bill.objects.create(
            farmer=self.farmer_user,
            amount=1500.00,
            description='Bund Maintenance Cess',
            status=Bill.Status.PENDING
        )
        Bill.objects.create(
            farmer=self.farmer_user,
            amount=800.00,
            description='Fertilizer Delivery Charge',
            status=Bill.Status.PAID
        )

        # Create a notification
        notif = Notification.objects.create(
            title='Monsoon Advisory Alert',
            message='All padasekharam committees to initiate dewatering operations by Friday.',
            posted_by=self.admin
        )

        res = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Monsoon Advisory Alert')
        self.assertContains(res, 'Total Farmers')
        self.assertContains(res, 'Total Mill Owners')
        self.assertContains(res, 'Pending Bills')
        self.assertEqual(res.context['total_farmers'], 1)
        self.assertEqual(res.context['total_millowners'], 1)
        self.assertEqual(res.context['pending_bills_count'], 1)
        self.assertIn(notif, res.context['recent_notifications'])

    def test_farmer_list_view(self):
        self.client.login(username='superadmin', password='Password123!')

        res = self.client.get(reverse('admin_farmer_list'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Raman Kutty')
        self.assertContains(res, 'Kainakary')
        self.assertContains(res, '9447123456')
        detail_url = reverse('admin_farmer_detail', args=[self.farmer_profile.id])
        self.assertContains(res, detail_url)

    def test_farmer_detail_view_with_fields(self):
        self.client.login(username='superadmin', password='Password123!')

        res = self.client.get(reverse('admin_farmer_detail', args=[self.farmer_profile.id]))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Raman Kutty')
        self.assertContains(res, 'PDN1005')
        self.assertContains(res, '9447123456')
        self.assertContains(res, 'North Polder Parcel 1')
        self.assertContains(res, 'East Canal Plot')
        self.assertContains(res, 'SY-104/A')
        self.assertEqual(len(res.context['fields']), 2)

    def test_bill_management_and_add_bill(self):
        self.client.login(username='superadmin', password='Password123!')

        # POST Add Bill
        res = self.client.post(reverse('admin_bills'), {
            'farmer': self.farmer_user.id,
            'amount': '3200.50',
            'description': 'Polder Pumping Electricity Bill',
        })
        self.assertEqual(res.status_code, 302)
        self.assertTrue(Bill.objects.filter(amount=3200.50, farmer=self.farmer_user).exists())
        new_bill = Bill.objects.get(amount=3200.50, farmer=self.farmer_user)
        self.assertEqual(new_bill.status, Bill.Status.PENDING)

        # GET Bill Management with filter
        res_get = self.client.get(reverse('admin_bills') + '?status=PENDING')
        self.assertEqual(res_get.status_code, 200)
        self.assertContains(res_get, '3200.50')
        self.assertContains(res_get, 'Polder Pumping Electricity Bill')

    def test_toggle_bill_status(self):
        self.client.login(username='superadmin', password='Password123!')

        bill = Bill.objects.create(
            farmer=self.farmer_user,
            amount=1200.00,
            description='Canal dredging dues',
            status=Bill.Status.PENDING
        )

        # Toggle to PAID
        res = self.client.post(reverse('toggle_bill_status', args=[bill.id]))
        self.assertEqual(res.status_code, 302)
        bill.refresh_from_db()
        self.assertEqual(bill.status, Bill.Status.PAID)

        # Toggle back to PENDING
        res2 = self.client.post(reverse('toggle_bill_status', args=[bill.id]))
        self.assertEqual(res2.status_code, 302)
        bill.refresh_from_db()
        self.assertEqual(bill.status, Bill.Status.PENDING)

    def test_post_notification_view(self):
        self.client.login(username='superadmin', password='Password123!')

        res = self.client.post(reverse('post_notification'), {
            'title': 'Subsidy Distribution Update',
            'message': 'Paddy procurement subsidy has been credited to registered accounts.',
        })
        self.assertEqual(res.status_code, 302)
        self.assertTrue(Notification.objects.filter(title='Subsidy Distribution Update').exists())
        notif = Notification.objects.get(title='Subsidy Distribution Update')
        self.assertEqual(notif.posted_by, self.admin)

    def test_issue_bill_dropdown_and_file_upload(self):
        self.client.login(username='superadmin', password='Password123!')

        fake_jpg = SimpleUploadedFile(
            name="tractor_voucher.jpg",
            content=b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01test-image-bytes",
            content_type="image/jpeg"
        )

        res = self.client.post(reverse('admin_bills'), {
            'farmer': self.farmer_user.id,
            'description': 'Tractor Bill',
            'amount': '4500.00',
            'bill_file': fake_jpg,
            'notes': 'Ploughing Block B 3.5 acres',
        })
        self.assertEqual(res.status_code, 302)

        bill = Bill.objects.get(farmer=self.farmer_user, amount=4500.00)
        self.assertEqual(bill.description, 'Tractor Bill')
        self.assertEqual(bill.notes, 'Ploughing Block B 3.5 acres')
        self.assertTrue(bill.bill_file.name.endswith('.jpg'))
        self.assertTrue(bill.is_image)
        self.assertFalse(bill.is_pdf)
        self.assertEqual(bill.file_name, 'tractor_voucher.jpg')

        # Clean up uploaded file
        if bill.bill_file and os.path.exists(bill.bill_file.path):
            os.remove(bill.bill_file.path)

    def test_issue_bill_invalid_file_extension(self):
        self.client.login(username='superadmin', password='Password123!')

        fake_exe = SimpleUploadedFile(
            name="malware.exe",
            content=b"MZ\x90fake-executable",
            content_type="application/octet-stream"
        )

        res = self.client.post(reverse('admin_bills'), {
            'farmer': self.farmer_user.id,
            'description': 'Seeds Bill',
            'amount': '1500.00',
            'bill_file': fake_exe,
        })
        self.assertEqual(res.status_code, 200)
        self.assertFormError(res.context['form'], 'bill_file', 'Only PDF and image files (.jpg, .jpeg, .png) are permitted.')
        self.assertFalse(Bill.objects.filter(amount=1500.00, farmer=self.farmer_user).exists())

    def test_admin_toggle_and_resolve_dispute(self):
        self.client.login(username='superadmin', password='Password123!')

        disputed_bill = Bill.objects.create(
            farmer=self.farmer_user,
            amount=2100.00,
            description='Bund Maintenance',
            status=Bill.Status.DISPUTED,
            dispute_reason='Acreage incorrect'
        )

        # Admin toggles to resolve and mark as PAID
        res = self.client.post(reverse('toggle_bill_status', args=[disputed_bill.id]))
        self.assertEqual(res.status_code, 302)
        disputed_bill.refresh_from_db()
        self.assertEqual(disputed_bill.status, Bill.Status.PAID)
