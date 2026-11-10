from decimal import Decimal
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.tests.factories import create_school, create_user, set_client_auth_cookies
from billing.models import (
    Invoice,
    InvoiceLine,
    Payment,
    Plan,
    PromotionRedemption,
    SchoolSubscription,
    TopUpPurchase,
)
from billing.services.catalog import seed_default_plans, seed_first_year_free_campaign
from billing.services.catalog_topups import seed_default_topup_packages
from billing.services.payments import fulfill_payment, handle_paystack_webhook_event
from billing.services.paystack import to_pesewas, verify_webhook_signature
from billing.services.subscriptions import start_subscription
from billing.services.upgrades import apply_capacity_upgrade
from communications.models import CreditAccount
from communications.services.ledger import get_balances


@override_settings(
    PAYSTACK_SAAS_SECRET_KEY='sk_test_secret',
    PAYSTACK_SAAS_WEBHOOK_SECRET='sk_test_secret',
    FRONTEND_URL='http://localhost:3003',
)
class BillingPhase5PaymentTests(APITestCase):
    def setUp(self):
        seed_default_plans()
        seed_first_year_free_campaign()
        seed_default_topup_packages()
        self.school = create_school(name='Pay School', phone_number='+233244000101')
        self.admin = create_user(
            school=self.school,
            is_active=True,
            phone_number='+233244000102',
            email='admin-pay@test.com',
        )
        set_client_auth_cookies(self.client, self.admin)
        self.subscription = start_subscription(
            school=self.school,
            plan=Plan.objects.get(code='starter'),
            apply_first_year_free=True,
        )

    def _fake_initialize(self, **kwargs):
        return {
            'authorization_url': f'https://checkout.paystack.com/{kwargs["reference"]}',
            'access_code': 'access_test',
            'reference': kwargs['reference'],
            'raw': {'status': True, 'data': {'reference': kwargs['reference']}},
        }

    def test_webhook_signature_hmac(self):
        body = b'{"event":"charge.success"}'
        import hashlib
        import hmac

        sig = hmac.new(b'sk_test_secret', body, hashlib.sha512).hexdigest()
        self.assertTrue(verify_webhook_signature(body=body, signature=sig))
        self.assertFalse(verify_webhook_signature(body=body, signature='bad'))

    @patch('billing.services.payments.initialize_transaction')
    def test_topup_checkout_and_fulfill_grants_credits(self, mock_init):
        mock_init.side_effect = self._fake_initialize
        url = reverse('school-billing-topup-purchase')
        response = self.client.post(url, {'package_code': 'sms-100'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reference = response.data['reference']
        payment = Payment.objects.get(reference=reference)
        self.assertEqual(payment.purpose, Payment.Purpose.TOPUP)
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertTrue(payment.authorization_url)

        purchase = TopUpPurchase.objects.get(payment=payment)
        self.assertEqual(purchase.credits, 100)

        fulfill_payment(
            payment=payment,
            provider_payload={'event': 'charge.success'},
            provider_transaction_id='txn_1',
            amount_ghs=payment.amount_ghs,
        )
        payment.refresh_from_db()
        purchase.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertEqual(purchase.status, TopUpPurchase.Status.PAID)
        self.assertEqual(get_balances(self.school)['sms'], 100)

        # Idempotent second fulfill
        fulfill_payment(payment=payment)
        self.assertEqual(get_balances(self.school)['sms'], 100)
        self.assertEqual(
            CreditAccount.objects.get(school=self.school, channel='sms').balance,
            100,
        )

    @patch('billing.services.payments.initialize_transaction')
    def test_invoice_pay_and_webhook_idempotent(self, mock_init):
        mock_init.side_effect = self._fake_initialize
        starter = Plan.objects.get(code='starter')
        basic = Plan.objects.get(code='basic')
        # The complimentary year would zero this upgrade. The pay test needs a balance.
        PromotionRedemption.objects.filter(school=self.school).update(revoked_at=timezone.now())
        _, invoice = apply_capacity_upgrade(
            school=self.school,
            new_plan=basic,
            mark_paid=False,
        )
        self.assertEqual(invoice.status, Invoice.Status.OPEN)
        self.assertTrue(invoice.total_ghs > 0)

        pay_url = reverse('school-billing-invoice-pay', kwargs={'pk': invoice.pk})
        response = self.client.post(pay_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reference = response.data['reference']
        payment = Payment.objects.get(reference=reference)

        event = {
            'event': 'charge.success',
            'data': {
                'id': 999,
                'reference': reference,
                'amount': to_pesewas(payment.amount_ghs),
                'status': 'success',
            },
        }
        first = handle_paystack_webhook_event(event)
        second = handle_paystack_webhook_event(event)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.status, Payment.Status.SUCCESS)

        invoice.refresh_from_db()
        self.subscription.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertEqual(self.subscription.plan_id, basic.pk)
        # starter was previous — plan applied via proration confirm
        self.assertNotEqual(self.subscription.plan_id, starter.pk)

    def test_webhook_endpoint_rejects_bad_signature(self):
        url = reverse('school-billing-paystack-webhook')
        response = self.client.post(
            url,
            data=b'{"event":"charge.success","data":{}}',
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE='invalid',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('billing.services.payments.initialize_transaction')
    def test_webhook_endpoint_fulfills(self, mock_init):
        mock_init.side_effect = self._fake_initialize
        pay_resp = self.client.post(
            reverse('school-billing-topup-purchase'),
            {'package_code': 'email-500'},
            format='json',
        )
        reference = pay_resp.data['reference']
        payment = Payment.objects.get(reference=reference)
        body = (
            '{'
            f'"event":"charge.success","data":{{"id":1,"reference":"{reference}",'
            f'"amount":{to_pesewas(payment.amount_ghs)},"status":"success"}}'
            '}'
        ).encode('utf-8')
        import hashlib
        import hmac

        sig = hmac.new(b'sk_test_secret', body, hashlib.sha512).hexdigest()
        response = self.client.post(
            reverse('school-billing-paystack-webhook'),
            data=body,
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE=sig,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertEqual(get_balances(self.school)['email'], 500)
