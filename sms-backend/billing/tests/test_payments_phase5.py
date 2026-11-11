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
        self.assertEqual(response.data['access_code'], 'access_test')

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

    def test_dashboard_webhook_path_rejects_bad_signature(self):
        response = self.client.post(
            '/api/payments/paystack/webhook/',
            data=b'{"event":"charge.success","data":{}}',
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE='invalid',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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

    @patch('billing.services.payments.initialize_transaction')
    def test_topup_invoice_is_not_a_second_payment(self, mock_init):
        mock_init.side_effect = self._fake_initialize
        started = self.client.post(
            reverse('school-billing-topup-purchase'),
            {'package_code': 'sms-100'},
            format='json',
        )
        self.assertEqual(started.status_code, status.HTTP_200_OK, started.data)
        invoice_id = started.data['invoice']
        pay = self.client.post(reverse('school-billing-invoice-pay', kwargs={'pk': invoice_id}))
        self.assertEqual(pay.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Payment.objects.filter(invoice_id=invoice_id).count(), 1)

        source = Payment.objects.get(reference=started.data['reference'])
        duplicate = Payment.objects.create(
            school=self.school,
            invoice_id=invoice_id,
            purpose=Payment.Purpose.INVOICE,
            provider=Payment.Provider.PAYSTACK,
            status=Payment.Status.PENDING,
            amount_ghs=source.amount_ghs,
            currency='GHS',
            reference='inv_duplicate_topup',
        )
        listed = self.client.get(reverse('school-billing-payments'))
        self.assertEqual(listed.status_code, status.HTTP_200_OK, listed.data)
        references = [row['reference'] for row in listed.data['results']]
        self.assertIn(source.reference, references)
        self.assertNotIn(duplicate.reference, references)

        upcoming = self.client.get(reverse('school-billing-upcoming'))
        self.assertNotEqual(upcoming.data.get('open_invoice_id'), str(invoice_id))

    def test_platform_topup_is_recorded_as_paid_and_audited(self):
        from django.conf import settings

        from platform_admin.models import PlatformAuditLog, PlatformUser

        ops = PlatformUser.objects.create_user(
            email='topup-ops@schoolasst.test',
            password='SecurePass123!',
        )
        platform = self.client_class()
        login = platform.post(
            reverse('platform-login'),
            {'email': ops.email, 'password': 'SecurePass123!'},
            format='json',
        )
        platform.cookies[settings.PLATFORM_JWT['AUTH_COOKIE']] = (
            login.cookies[settings.PLATFORM_JWT['AUTH_COOKIE']].value
        )
        response = platform.post(
            reverse('platform-school-topup', kwargs={'pk': self.school.pk}),
            {'package_code': 'sms-100'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['credits'], 100)
        self.assertEqual(response.data['status'], 'paid')
        self.assertEqual(get_balances(self.school)['sms'], 100)
        payment = Payment.objects.get(school=self.school, purpose=Payment.Purpose.TOPUP)
        self.assertEqual(payment.provider, Payment.Provider.MANUAL)
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        purchase = TopUpPurchase.objects.get(payment=payment)
        self.assertEqual(purchase.status, TopUpPurchase.Status.PAID)
        audit = PlatformAuditLog.objects.get(
            action='billing.topup.recorded_paid',
            target_id=str(self.school.pk),
        )
        self.assertTrue(audit.detail['recorded_as_paid'])
        self.assertEqual(audit.detail['package_code'], 'sms-100')
        self.assertEqual(audit.actor_id, ops.pk)

    @patch('billing.services.payments.verify_transaction')
    @patch('billing.services.payments.initialize_transaction')
    def test_platform_verify_completes_a_confirmed_payment(self, mock_init, mock_verify):
        from django.conf import settings

        from billing.services.paystack import to_pesewas
        from platform_admin.models import PlatformAuditLog, PlatformUser

        mock_init.side_effect = self._fake_initialize
        started = self.client.post(
            reverse('school-billing-topup-purchase'),
            {'package_code': 'sms-100'},
            format='json',
        )
        self.assertEqual(started.status_code, status.HTTP_200_OK, started.data)
        payment = Payment.objects.get(reference=started.data['reference'])
        mock_verify.return_value = {
            'status': 'success',
            'amount': to_pesewas(payment.amount_ghs),
            'id': 99,
        }
        ops = PlatformUser.objects.create_user(
            email='verify-ops@schoolasst.test',
            password='SecurePass123!',
        )
        platform = self.client_class()
        login = platform.post(
            reverse('platform-login'),
            {'email': ops.email, 'password': 'SecurePass123!'},
            format='json',
        )
        platform.cookies[settings.PLATFORM_JWT['AUTH_COOKIE']] = (
            login.cookies[settings.PLATFORM_JWT['AUTH_COOKIE']].value
        )
        verified = platform.post(
            reverse('platform-payment-verify', kwargs={'pk': payment.pk}),
        )
        self.assertEqual(verified.status_code, status.HTTP_200_OK, verified.data)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertEqual(get_balances(self.school)['sms'], 100)
        audit = PlatformAuditLog.objects.get(
            action='billing.payment.verified',
            target_id=str(self.school.pk),
        )
        self.assertEqual(audit.detail['outcome'], 'success')
        self.assertEqual(audit.detail['reference'], payment.reference)

    @patch('billing.services.payments.verify_transaction')
    @patch('billing.services.payments.initialize_transaction')
    def test_platform_verify_leaves_an_unconfirmed_payment(self, mock_init, mock_verify):
        from django.conf import settings

        from platform_admin.models import PlatformUser

        mock_init.side_effect = self._fake_initialize
        started = self.client.post(
            reverse('school-billing-topup-purchase'),
            {'package_code': 'email-500'},
            format='json',
        )
        payment = Payment.objects.get(reference=started.data['reference'])
        mock_verify.return_value = {'status': 'abandoned', 'amount': 0, 'id': 1}
        ops = PlatformUser.objects.create_user(
            email='verify-ops-2@schoolasst.test',
            password='SecurePass123!',
        )
        platform = self.client_class()
        login = platform.post(
            reverse('platform-login'),
            {'email': ops.email, 'password': 'SecurePass123!'},
            format='json',
        )
        platform.cookies[settings.PLATFORM_JWT['AUTH_COOKIE']] = (
            login.cookies[settings.PLATFORM_JWT['AUTH_COOKIE']].value
        )
        verified = platform.post(
            reverse('platform-payment-verify', kwargs={'pk': payment.pk}),
        )
        self.assertEqual(verified.status_code, status.HTTP_400_BAD_REQUEST)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PENDING)
