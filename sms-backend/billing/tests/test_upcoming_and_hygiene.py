from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.tests.factories import create_school, create_user, set_client_auth_cookies
from billing.models import Invoice, InvoiceLine, Plan, SchoolSubscription
from billing.services.catalog import seed_default_plans, seed_first_year_free_campaign
from billing.services.invoice_hygiene import void_obsolete_interval_change_invoices
from billing.services.invoices import create_invoice_with_lines
from billing.services.subscriptions import start_subscription
from django.utils import timezone


class UpcomingAndHygieneTests(APITestCase):
    def setUp(self):
        seed_default_plans()
        seed_first_year_free_campaign()
        self.school = create_school(name='Upcoming School', phone_number='+233244000301')
        self.admin = create_user(
            school=self.school,
            is_active=True,
            phone_number='+233244000302',
            email='upcoming@test.com',
        )
        set_client_auth_cookies(self.client, self.admin)
        self.subscription = start_subscription(
            school=self.school,
            plan=Plan.objects.get(code='starter'),
            apply_first_year_free=True,
            interval=SchoolSubscription.Interval.MONTHLY,
        )

    def test_upcoming_endpoint_returns_combined_bill(self):
        url = reverse('school-billing-upcoming')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_ghs', response.data)
        self.assertIn('lines', response.data)
        self.assertTrue(any(line['kind'] == 'application' for line in response.data['lines']))
        self.assertTrue(any(line['kind'] == 'discount' for line in response.data['lines']))

    def test_void_interval_change_invoices_and_hide_from_list(self):
        now = timezone.now()
        create_invoice_with_lines(
            school=self.school,
            subscription=self.subscription,
            period_start=now,
            period_end=self.subscription.current_period_end,
            lines=[
                {
                    'kind': InvoiceLine.Kind.INTERVAL_CHANGE,
                    'description': 'Interval change monthly → annual',
                    'quantity': '1',
                    'unit_price_ghs': '100.00',
                    'amount_ghs': '100.00',
                    'metadata': {'reason': 'interval_change'},
                },
            ],
            notes='Mid-period interval change (monthly → annual)',
            mark_paid_if_zero=False,
        )
        create_invoice_with_lines(
            school=self.school,
            subscription=self.subscription,
            period_start=now,
            period_end=self.subscription.current_period_end,
            lines=[
                {
                    'kind': InvoiceLine.Kind.INTERVAL_CHANGE,
                    'description': 'Interval change monthly → annual',
                    'quantity': '1',
                    'unit_price_ghs': '100.00',
                    'amount_ghs': '100.00',
                    'metadata': {'reason': 'interval_change'},
                },
            ],
            notes='Mid-period interval change (monthly → annual)',
            mark_paid_if_zero=False,
        )
        self.assertEqual(
            Invoice.objects.filter(school=self.school, status=Invoice.Status.OPEN).count(),
            2,
        )
        voided = void_obsolete_interval_change_invoices(school=self.school)
        self.assertEqual(voided, 2)

        list_url = reverse('school-billing-invoices')
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all(row['status'] != 'void' for row in response.data['results']))
        notes = [row.get('notes') for row in response.data['results']]
        self.assertNotIn('Mid-period interval change (monthly → annual)', notes)
