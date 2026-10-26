"""
Management command to seed the PaddyNet database with realistic demo data.

Usage:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --clear   # wipe existing demo data first
"""
import random
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, cast

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from farms.models import FarmerProfile, Field, FarmingActivity
from millowner.models import MillOwnerProfile, Bid
from billing.models import Bill
from notices.models import Notification

User = get_user_model()


FARMER_DATA: list[dict[str, Any]] = [
    {
        'email': 'rajan.padmanabhan@paddynet.demo',
        'full_name': 'Rajan Padmanabhan',
        'phone_number': '+919876543210',
        'acres_owned': Decimal('4.50'),
        'farmer_id': 'PDN1001',
        'fields': [
            {
                'field_name': 'Kayal North Polder',
                'location': 'Kainakary North Ward',
                'extent_area': Decimal('2.50'),
                'field_identifier': 'SY-104/2',
                'activities': [
                    {'type': 'SOWING',       'date': date(2026, 6, 10), 'season': '2026 Kharif', 'notes': 'Uma variety seeds, 25 kg/acre'},
                    {'type': 'FERTILIZER',   'date': date(2026, 7, 5),  'season': '2026 Kharif', 'notes': 'Urea 50 kg applied, basal dose'},
                    {'type': 'IRRIGATION',   'date': date(2026, 7, 20), 'season': '2026 Kharif', 'notes': 'Pump irrigation, 3 hours'},
                    {'type': 'PESTICIDE',    'date': date(2026, 8, 1),  'season': '2026 Kharif', 'notes': 'Monocrotophos spray for stem borer'},
                    {'type': 'HARVEST',      'date': date(2026, 9, 25), 'season': '2026 Kharif', 'yield_kg': Decimal('7500'), 'notes': 'Good yield; grain quality excellent'},
                ],
            },
            {
                'field_name': 'East Block Padasekharam',
                'location': 'Kainakary Ward 3',
                'extent_area': Decimal('2.00'),
                'field_identifier': 'SY-201/A',
                'activities': [
                    {'type': 'SOWING',    'date': date(2026, 6, 15), 'season': '2026 Kharif', 'notes': 'Jyothi variety, wet nursery raised'},
                    {'type': 'FERTILIZER','date': date(2026, 7, 10), 'season': '2026 Kharif', 'notes': 'DAP 40 kg, MOP 25 kg'},
                    {'type': 'HARVEST',   'date': date(2026, 9, 28), 'season': '2026 Kharif', 'yield_kg': Decimal('5800'), 'notes': 'Slightly lower yield due to waterlogging'},
                ],
            },
        ],
    },
    {
        'email': 'leela.kumari@paddynet.demo',
        'full_name': 'Leela Kumari',
        'phone_number': '+919876543211',
        'acres_owned': Decimal('3.00'),
        'farmer_id': 'PDN1002',
        'fields': [
            {
                'field_name': 'South Kayal Plot',
                'location': 'Kainakary Ward 7',
                'extent_area': Decimal('3.00'),
                'field_identifier': 'SY-307',
                'activities': [
                    {'type': 'SOWING',       'date': date(2026, 6, 8),  'season': '2026 Kharif', 'notes': 'Kanchana variety, direct seeded'},
                    {'type': 'TRANSPLANTING','date': date(2026, 6, 28), 'season': '2026 Kharif', 'notes': 'Gap filling transplanting done'},
                    {'type': 'FERTILIZER',   'date': date(2026, 7, 12), 'season': '2026 Kharif', 'notes': 'Neem-coated urea 60 kg applied'},
                    {'type': 'IRRIGATION',   'date': date(2026, 8, 3),  'season': '2026 Kharif', 'notes': 'Channel irrigation opened for 4 hrs'},
                    {'type': 'HARVEST',      'date': date(2026, 9, 30), 'season': '2026 Kharif', 'yield_kg': Decimal('9200'), 'notes': 'Excellent season, high market price expected'},
                ],
            },
        ],
    },
    {
        'email': 'suresh.varma@paddynet.demo',
        'full_name': 'Suresh Varma',
        'phone_number': '+919876543212',
        'acres_owned': Decimal('6.00'),
        'farmer_id': 'PDN1003',
        'fields': [
            {
                'field_name': 'Pullu Kayal Block A',
                'location': 'Kainakary Padasekharam A',
                'extent_area': Decimal('3.50'),
                'field_identifier': 'PA-001',
                'activities': [
                    {'type': 'SOWING',     'date': date(2026, 6, 5),  'season': '2026 Kharif', 'notes': 'Improved Jaya variety'},
                    {'type': 'FERTILIZER', 'date': date(2026, 7, 1),  'season': '2026 Kharif', 'notes': 'Basal: DAP 50 kg + MOP 30 kg'},
                    {'type': 'PESTICIDE',  'date': date(2026, 7, 25), 'season': '2026 Kharif', 'notes': 'Fungicide for blast prevention'},
                    {'type': 'HARVEST',    'date': date(2026, 9, 20), 'season': '2026 Kharif', 'yield_kg': Decimal('10850'), 'notes': 'Record yield for this parcel'},
                ],
            },
            {
                'field_name': 'Pullu Kayal Block B',
                'location': 'Kainakary Padasekharam B',
                'extent_area': Decimal('2.50'),
                'field_identifier': 'PA-002',
                'activities': [
                    {'type': 'SOWING',   'date': date(2025, 11, 10), 'season': '2025 Rabi', 'notes': 'PTB-39 variety, dry season'},
                    {'type': 'FERTILIZER','date': date(2025, 12, 5), 'season': '2025 Rabi', 'notes': 'Split application: urea 30+30 kg'},
                    {'type': 'HARVEST',  'date': date(2026, 2, 28),  'season': '2025 Rabi', 'yield_kg': Decimal('7200'), 'notes': 'Good rabi harvest, sold locally'},
                ],
            },
        ],
    },
]

MILLOWNER_DATA = [
    {
        'email': 'swasthik.mill@paddynet.demo',
        'mill_name': 'Swasthik Rice Mill',
        'mill_location': 'Ambalappuzha, Alappuzha',
        'phone_number': '+919812345678',
        'fssai_license_number': '11224567891234',
    },
    {
        'email': 'kerala.agromill@paddynet.demo',
        'mill_name': 'Kerala Agro Rice Mill',
        'mill_location': 'Cherthala, Alappuzha',
        'phone_number': '+919812345679',
        'fssai_license_number': '11234567891235',
    },
]

NOTIFICATIONS = [
    {
        'title': 'Kharif 2026 Water Release Schedule Published',
        'message': (
            'The Kainakary Padasekharam Water Users Association has published the irrigation water '
            'release schedule for Kharif 2026. Water release will commence on June 5 and continue '
            'through October 15. Farmers are advised to maintain bund levels and report any leaks '
            'to the ward committee within 24 hours. Please coordinate with your block supervisors '
            'for pump scheduling.'
        ),
    },
    {
        'title': 'Paddy Procurement Price Revision — October 2026',
        'message': (
            'The Government of Kerala has revised the Minimum Support Price (MSP) for paddy to '
            '₹2,183 per quintal (100 kg) effective October 1, 2026. Farmers are encouraged to '
            'register their harvest quantities with the PaddyNet admin portal to participate in '
            'the state procurement drive. Mill owners placing bids below MSP will be flagged.'
        ),
    },
    {
        'title': 'Free Soil Health Card Camp — November 2026',
        'message': (
            'The Kainakary Krishi Bhavan will conduct a free Soil Health Card assessment camp '
            'on November 12–14, 2026. All registered farmers are requested to bring 500g soil '
            'samples from their primary paddy fields. Reports will be provided within 7 working '
            'days. Contact the Krishi Bhavan helpline for appointment booking.'
        ),
    },
]


class Command(BaseCommand):
    help = 'Seeds the PaddyNet database with realistic demo data for 3 farmers, 2 mill owners, bids, bills, and notifications.'
    style: Any

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all existing demo data (emails ending with @paddynet.demo) before seeding.',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing demo data...'))
            User.objects.filter(email__endswith='@paddynet.demo').delete()
            self.stdout.write(self.style.SUCCESS('Demo data cleared.'))

        with cast(Any, transaction.atomic()):
            admin_user = self._get_or_create_admin()
            farmer_users = self._create_farmers()
            mill_users = self._create_millowners()
            self._create_bids(mill_users, farmer_users)
            self._create_bills(admin_user, farmer_users)
            self._create_notifications(admin_user)

        self.stdout.write(self.style.SUCCESS('\n✅ Demo data seeding complete!'))
        self.stdout.write('  Farmers:       3  (rajan, leela, suresh — password: Demo@1234)')
        self.stdout.write('  Mill Owners:   2  (swasthik, kerala — password: Demo@1234)')
        self.stdout.write('  Admin:         admin@paddynet.demo  (password: Admin@1234)')

    def _get_or_create_admin(self):
        """Ensure at least one admin/superuser exists for notifications."""
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            admin = User.objects.create_superuser(
                username='paddynet_admin',
                email='admin@paddynet.demo',
                password='Admin@1234',
            )
            admin.role = 'ADMIN'
            admin.save()
            self.stdout.write(self.style.SUCCESS(f'  Created admin: admin@paddynet.demo'))
        return admin

    def _create_farmers(self):
        farmer_users = []
        for fd in FARMER_DATA:
            if User.objects.filter(email=fd['email']).exists():
                user = User.objects.get(email=fd['email'])
                self.stdout.write(f'  [skip] Farmer already exists: {fd["email"]}')
                farmer_users.append(user)
                continue

            user = User.objects.create_user(
                username=fd['full_name'].lower().replace(' ', '_'),
                email=fd['email'],
                password='Demo@1234',
                first_name=fd['full_name'],
                role='FARMER',
            )
            profile = FarmerProfile.objects.create(
                user=user,
                full_name=fd['full_name'],
                village='Kainakary',
                phone_number=fd['phone_number'],
                acres_owned=fd['acres_owned'],
                farming_group='A BLOCK',
                farmer_id=fd['farmer_id'],
                is_verified=True,
            )
            self.stdout.write(self.style.SUCCESS(f'  Created farmer: {fd["full_name"]} ({fd["farmer_id"]})'))

            for field_data in fd['fields']:
                field = Field.objects.create(
                    owner=user,
                    field_name=field_data['field_name'],
                    location=field_data['location'],
                    extent_area=field_data['extent_area'],
                    field_identifier=field_data.get('field_identifier', ''),
                )
                for act in field_data['activities']:
                    FarmingActivity.objects.create(
                        field=field,
                        activity_type=act['type'],
                        activity_date=act['date'],
                        season_year=act['season'],
                        yield_kg=act.get('yield_kg'),
                        notes=act.get('notes', ''),
                    )
                self.stdout.write(f'    + Field: {field_data["field_name"]} ({len(field_data["activities"])} activities)')

            farmer_users.append(user)
        return farmer_users

    def _create_millowners(self):
        mill_users = []
        for md in MILLOWNER_DATA:
            if User.objects.filter(email=md['email']).exists():
                user = User.objects.get(email=md['email'])
                self.stdout.write(f'  [skip] Mill owner already exists: {md["email"]}')
                mill_users.append(user)
                continue

            username = md['mill_name'].lower().replace(' ', '_')
            user = User.objects.create_user(
                username=username,
                email=md['email'],
                password='Demo@1234',
                first_name=md['mill_name'],
                role='MILLOWNER',
            )
            MillOwnerProfile.objects.create(
                user=user,
                mill_name=md['mill_name'],
                mill_location=md['mill_location'],
                phone_number=md['phone_number'],
                fssai_license_number=md['fssai_license_number'],
                is_verified=True,
            )
            self.stdout.write(self.style.SUCCESS(f'  Created mill owner: {md["mill_name"]}'))
            mill_users.append(user)
        return mill_users

    def _create_bids(self, mill_users, farmer_users):
        # Place bids on fields with harvest activities
        harvested_fields = Field.objects.filter(
            activities__activity_type='HARVEST',
            owner__in=farmer_users,
        ).distinct()

        bid_data = [
            # (field_index, mill_index, amount, notes)
            (0, 0, Decimal('48000'), 'Ready for pickup within 3 days. Moisture max 14%.'),
            (0, 1, Decimal('46500'), 'Competitive offer — immediate payment on delivery.'),
            (1, 0, Decimal('31000'), 'Can arrange transport. Price includes packaging.'),
            (2, 0, Decimal('62000'), 'Top offer — premium paddy lot, priority procurement.'),
            (2, 1, Decimal('60500'), 'Offer valid for 5 days. ISO-certified storage facility.'),
            (3, 1, Decimal('55000'), 'Direct purchase, no intermediary.'),
        ]

        fields_list = list(harvested_fields)
        for field_idx, mill_idx, amount, notes in bid_data:
            if field_idx < len(fields_list) and mill_idx < len(mill_users):
                field = fields_list[field_idx]
                mill = mill_users[mill_idx]
                if not Bid.objects.filter(field=field, millowner=mill, amount=amount).exists():
                    Bid.objects.create(field=field, millowner=mill, amount=amount, notes=notes)
                    self.stdout.write(f'  Bid: ₹{amount} on "{field.field_name}" by {mill.first_name}')

    def _create_bills(self, admin_user, farmer_users):
        bill_data = [
            (0, Decimal('1800'), 'Bund maintenance levy — Kharif 2026'),
            (0, Decimal('650'),  'Water pumping charges — July 2026'),
            (1, Decimal('1200'), 'Padasekharam maintenance fee — 2026'),
            (2, Decimal('2400'), 'Channel desilting contribution — 2026'),
            (2, Decimal('900'),  'Night watchman charges — Kharif season'),
        ]
        for idx, amount, desc in bill_data:
            if idx < len(farmer_users):
                farmer = farmer_users[idx]
                if not Bill.objects.filter(farmer=farmer, amount=amount, description=desc).exists():
                    Bill.objects.create(farmer=farmer, amount=amount, description=desc)
                    self.stdout.write(f'  Bill: ₹{amount} for {farmer.first_name} — {desc}')

    def _create_notifications(self, admin_user):
        for nd in NOTIFICATIONS:
            if not Notification.objects.filter(title=nd['title']).exists():
                Notification.objects.create(
                    title=nd['title'],
                    message=nd['message'],
                    posted_by=admin_user,
                )
                self.stdout.write(f'  Notice: {nd["title"][:60]}...')
