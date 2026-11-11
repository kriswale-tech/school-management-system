from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from billing.models import (
    Invoice,
    InvoiceLine,
    Payment,
    SchoolSubscription,
    TopUpPackage,
    TopUpPurchase,
)
from billing.services.invoices import create_invoice_with_lines, mark_invoice_paid
from billing.services.paystack import (
    from_pesewas,
    initialize_transaction,
    make_reference,
    verify_transaction,
)
from billing.services.upgrades import confirm_capacity_upgrade_payment
from communications.services.ledger import grant_topup


def _callback_url(*, path: str = '/settings/billing') -> str:
    base = (getattr(settings, 'FRONTEND_URL', None) or 'http://localhost:3003').rstrip('/')
    return f'{base}{path}?payment=return'


def _payer_email(school) -> str:
    contact = (getattr(school, 'email', None) or '').strip()
    if contact:
        return contact
    return f'school-{school.pk}@billing.schoolasst.local'


def _assert_open_invoice(invoice: Invoice) -> None:
    if invoice.status == Invoice.Status.PAID:
        raise ValidationError({'detail': 'Invoice is already paid.'})
    if invoice.status != Invoice.Status.OPEN:
        raise ValidationError({'detail': 'Only open invoices can be paid.'})
    if invoice.total_ghs <= 0:
        raise ValidationError({'detail': 'Invoice total must be greater than zero.'})
    if invoice.lines.filter(kind=InvoiceLine.Kind.TOPUP).exists():
        raise ValidationError({
            'detail': (
                'This invoice is a credit top-up. Confirm that top-up charge '
                'instead of starting another payment.'
            ),
        })


@transaction.atomic
def start_invoice_checkout(*, school, invoice: Invoice, actor_user=None) -> Payment:
    if invoice.school_id != school.pk:
        raise ValidationError({'detail': 'Invoice does not belong to this school.'})
    _assert_open_invoice(invoice)

    existing = (
        Payment.objects.select_for_update()
        .filter(
            school=school,
            invoice=invoice,
            purpose=Payment.Purpose.INVOICE,
            status=Payment.Status.PENDING,
        )
        .order_by('-created_at')
        .first()
    )
    if existing and existing.authorization_url:
        return existing

    reference = make_reference('inv')
    payment = Payment.objects.create(
        school=school,
        invoice=invoice,
        purpose=Payment.Purpose.INVOICE,
        provider=Payment.Provider.PAYSTACK,
        status=Payment.Status.PENDING,
        amount_ghs=invoice.total_ghs,
        currency='GHS',
        reference=reference,
        metadata={
            'invoice_id': str(invoice.pk),
            'actor_user_id': str(getattr(actor_user, 'pk', '') or ''),
        },
    )
    init = initialize_transaction(
        email=_payer_email(school),
        amount_ghs=invoice.total_ghs,
        reference=reference,
        callback_url=_callback_url(),
        metadata={
            'payment_id': str(payment.pk),
            'school_id': str(school.pk),
            'invoice_id': str(invoice.pk),
            'purpose': Payment.Purpose.INVOICE,
        },
    )
    payment.authorization_url = init['authorization_url']
    payment.access_code = init['access_code']
    payment.raw_initialize = init.get('raw') or {}
    payment.save(
        update_fields=['authorization_url', 'access_code', 'raw_initialize', 'updated_at'],
    )
    return payment


@transaction.atomic
def start_topup_checkout(*, school, package: TopUpPackage, actor_user=None) -> Payment:
    if not package.is_active:
        raise ValidationError({'package_code': 'Package is not available.'})
    subscription = (
        SchoolSubscription.objects.filter(school=school, is_current=True)
        .select_related('plan')
        .first()
    )
    if subscription is None:
        raise ValidationError({'detail': 'School has no current subscription.'})

    now = timezone.now()
    invoice = create_invoice_with_lines(
        school=school,
        subscription=subscription,
        period_start=now,
        period_end=subscription.current_period_end,
        lines=[
            {
                'kind': InvoiceLine.Kind.TOPUP,
                'description': f'{package.name} (+{package.credits} {package.channel})',
                'quantity': '1',
                'unit_price_ghs': str(package.price_ghs),
                'amount_ghs': str(package.price_ghs),
                'metadata': {
                    'package_code': package.code,
                    'channel': package.channel,
                    'credits': package.credits,
                },
            },
        ],
        notes='Communication credit top-up',
        mark_paid_if_zero=False,
    )
    reference = make_reference('top')
    payment = Payment.objects.create(
        school=school,
        invoice=invoice,
        purpose=Payment.Purpose.TOPUP,
        provider=Payment.Provider.PAYSTACK,
        status=Payment.Status.PENDING,
        amount_ghs=package.price_ghs,
        currency='GHS',
        reference=reference,
        metadata={
            'package_code': package.code,
            'actor_user_id': str(getattr(actor_user, 'pk', '') or ''),
        },
    )
    purchase = TopUpPurchase.objects.create(
        school=school,
        package=package,
        invoice=invoice,
        payment=payment,
        channel=package.channel,
        credits=package.credits,
        amount_ghs=package.price_ghs,
        status=TopUpPurchase.Status.PENDING,
    )
    init = initialize_transaction(
        email=_payer_email(school),
        amount_ghs=package.price_ghs,
        reference=reference,
        callback_url=_callback_url(path='/settings/messaging'),
        metadata={
            'payment_id': str(payment.pk),
            'school_id': str(school.pk),
            'invoice_id': str(invoice.pk),
            'topup_purchase_id': str(purchase.pk),
            'purpose': Payment.Purpose.TOPUP,
        },
    )
    payment.authorization_url = init['authorization_url']
    payment.access_code = init['access_code']
    payment.raw_initialize = init.get('raw') or {}
    payment.save(
        update_fields=['authorization_url', 'access_code', 'raw_initialize', 'updated_at'],
    )
    return payment


@transaction.atomic
def record_paid_topup(*, school, package: TopUpPackage, actor=None, ip_address: str | None = None) -> TopUpPurchase:
    """Record a platform top-up as already paid and grant the credits. No Paystack charge."""
    from platform_admin.models import PlatformUser
    from platform_admin.services.audit import record_audit

    if not package.is_active:
        raise ValidationError({'package_code': 'Package is not available.'})
    subscription = (
        SchoolSubscription.objects.filter(school=school, is_current=True)
        .select_related('plan')
        .first()
    )
    if subscription is None:
        raise ValidationError({'detail': 'School has no current subscription.'})

    now = timezone.now()
    invoice = create_invoice_with_lines(
        school=school,
        subscription=subscription,
        period_start=now,
        period_end=subscription.current_period_end,
        lines=[
            {
                'kind': InvoiceLine.Kind.TOPUP,
                'description': f'{package.name} (+{package.credits} {package.channel})',
                'quantity': '1',
                'unit_price_ghs': str(package.price_ghs),
                'amount_ghs': str(package.price_ghs),
                'metadata': {
                    'package_code': package.code,
                    'channel': package.channel,
                    'credits': package.credits,
                    'recorded_by': 'platform',
                },
            },
        ],
        notes='Communication credit top-up recorded as paid by platform',
        mark_paid_if_zero=False,
    )
    reference = make_reference('top')
    payment = Payment.objects.create(
        school=school,
        invoice=invoice,
        purpose=Payment.Purpose.TOPUP,
        provider=Payment.Provider.MANUAL,
        status=Payment.Status.SUCCESS,
        amount_ghs=package.price_ghs,
        currency='GHS',
        reference=reference,
        paid_at=now,
        metadata={
            'package_code': package.code,
            'recorded_by': 'platform',
        },
    )
    purchase = TopUpPurchase.objects.create(
        school=school,
        package=package,
        invoice=invoice,
        payment=payment,
        channel=package.channel,
        credits=package.credits,
        amount_ghs=package.price_ghs,
        status=TopUpPurchase.Status.PENDING,
    )
    mark_invoice_paid(invoice, amount=package.price_ghs)
    entry = grant_topup(
        school=school,
        channel=package.channel,
        credits=package.credits,
        idempotency_key=f'topup:{reference}',
        invoice=invoice,
        metadata={
            'package_code': package.code,
            'payment_reference': reference,
            'recorded_by': 'platform',
        },
    )
    purchase.status = TopUpPurchase.Status.PAID
    purchase.ledger_entry = entry
    purchase.save(update_fields=['status', 'ledger_entry', 'updated_at'])
    record_audit(
        actor=actor if isinstance(actor, PlatformUser) else None,
        action='billing.topup.recorded_paid',
        target_type='school',
        target_id=str(school.pk),
        detail={
            'package_code': package.code,
            'package_name': package.name,
            'channel': package.channel,
            'credits': package.credits,
            'amount_ghs': f'{package.price_ghs:.2f}',
            'invoice_id': str(invoice.pk),
            'payment_reference': reference,
            'recorded_as_paid': True,
        },
        ip_address=ip_address,
    )
    return purchase


def _fulfill_topup(*, payment: Payment, invoice: Invoice) -> None:
    purchase = getattr(payment, 'topup_purchase', None)
    if purchase is None:
        purchase = TopUpPurchase.objects.filter(invoice=invoice).select_related('package').first()
    if purchase is None:
        raise ValidationError({'detail': 'Top-up purchase record missing.'})

    if invoice.status != Invoice.Status.PAID:
        mark_invoice_paid(invoice, amount=payment.amount_ghs)

    entry = grant_topup(
        school=payment.school,
        channel=purchase.channel,
        credits=purchase.credits,
        idempotency_key=f'topup:{payment.reference}',
        invoice=invoice,
        metadata={
            'package_code': purchase.package.code,
            'payment_reference': payment.reference,
        },
    )
    purchase.status = TopUpPurchase.Status.PAID
    purchase.ledger_entry = entry
    purchase.save(update_fields=['status', 'ledger_entry', 'updated_at'])


def apply_paid_invoice_effects(*, invoice: Invoice, payment: Payment | None = None) -> None:
    """Shared side-effects after an invoice becomes paid (Paystack or platform mark-paid)."""
    invoice = Invoice.objects.prefetch_related('lines').select_related('subscription').get(
        pk=invoice.pk,
    )

    if invoice.lines.filter(kind=InvoiceLine.Kind.APPLICATION_PRORATION).exists():
        confirm_capacity_upgrade_payment(invoice=invoice)
        from billing.services.dunning import reactivate_subscription_after_payment

        reactivate_subscription_after_payment(subscription=invoice.subscription)
        return

    if invoice.lines.filter(kind=InvoiceLine.Kind.INTERVAL_CHANGE).exists():
        from billing.services.interval_change import confirm_interval_change_payment

        confirm_interval_change_payment(invoice=invoice)
        return

    if invoice.lines.filter(kind=InvoiceLine.Kind.TOPUP).exists():
        if payment is None:
            payment = (
                Payment.objects.filter(invoice=invoice, purpose=Payment.Purpose.TOPUP)
                .order_by('-created_at')
                .first()
            )
        if payment is None:
            # Manual mark-paid without a Payment row — grant via purchase/invoice metadata.
            from billing.models import TopUpPurchase
            from communications.services.ledger import grant_topup as _grant

            purchase = TopUpPurchase.objects.filter(invoice=invoice).select_related('package').first()
            if purchase is None:
                line = invoice.lines.filter(kind=InvoiceLine.Kind.TOPUP).first()
                meta = (line.metadata if line else {}) or {}
                channel = meta.get('channel')
                credits = int(meta.get('credits') or 0)
                if channel and credits:
                    if invoice.status != Invoice.Status.PAID:
                        mark_invoice_paid(invoice)
                    _grant(
                        school=invoice.school,
                        channel=channel,
                        credits=credits,
                        idempotency_key=f'topup:invoice:{invoice.pk}',
                        invoice=invoice,
                        metadata=meta,
                    )
                return
            if invoice.status != Invoice.Status.PAID:
                mark_invoice_paid(invoice)
            entry = _grant(
                school=invoice.school,
                channel=purchase.channel,
                credits=purchase.credits,
                idempotency_key=f'topup:invoice:{invoice.pk}',
                invoice=invoice,
                metadata={'package_code': purchase.package.code},
            )
            purchase.status = TopUpPurchase.Status.PAID
            purchase.ledger_entry = entry
            purchase.save(update_fields=['status', 'ledger_entry', 'updated_at'])
            return
        _fulfill_topup(payment=payment, invoice=invoice)
        return

    if invoice.status != Invoice.Status.PAID:
        amount = payment.amount_ghs if payment is not None else None
        mark_invoice_paid(invoice, amount=amount)

    period = getattr(invoice, 'subscription_period', None)
    if period is not None:
        from communications.services.addons import allocate_period_addons

        subscription = invoice.subscription
        allocate_period_addons(
            subscription=subscription,
            period=period,
            invoice=invoice,
        )
    from billing.services.dunning import reactivate_subscription_after_payment

    reactivate_subscription_after_payment(subscription=invoice.subscription)


def _fulfill_invoice(*, payment: Payment, invoice: Invoice) -> None:
    apply_paid_invoice_effects(invoice=invoice, payment=payment)


@transaction.atomic
def fulfill_payment(
    *,
    payment: Payment,
    provider_payload: dict | None = None,
    provider_transaction_id: str = '',
    amount_ghs: Decimal | None = None,
) -> Payment:
    payment = (
        Payment.objects.select_for_update(of=('self',))
        .select_related('invoice', 'school')
        .get(pk=payment.pk)
    )
    if payment.status == Payment.Status.SUCCESS:
        return payment

    if amount_ghs is not None and Decimal(amount_ghs) != payment.amount_ghs:
        raise ValidationError({
            'detail': (
                f'Paid amount {amount_ghs} does not match expected {payment.amount_ghs}.'
            ),
        })

    payment.status = Payment.Status.SUCCESS
    payment.paid_at = timezone.now()
    payment.provider_transaction_id = provider_transaction_id or payment.provider_transaction_id
    if provider_payload is not None:
        payment.raw_webhook = provider_payload
    payment.save(
        update_fields=[
            'status',
            'paid_at',
            'provider_transaction_id',
            'raw_webhook',
            'updated_at',
        ],
    )

    invoice = payment.invoice
    if invoice is not None:
        invoice = Invoice.objects.select_for_update().prefetch_related('lines').get(pk=invoice.pk)
        apply_paid_invoice_effects(invoice=invoice, payment=payment)

    return payment


@transaction.atomic
def verify_and_fulfill(*, reference: str) -> Payment:
    payment = (
        Payment.objects.select_for_update(of=('self',))
        .select_related('invoice', 'school')
        .filter(reference=reference)
        .first()
    )
    if payment is None:
        raise ValidationError({'reference': 'Unknown payment reference.'})
    if payment.status == Payment.Status.SUCCESS:
        return payment

    data = verify_transaction(reference)
    status = (data.get('status') or '').lower()
    if status != 'success':
        payment.status = Payment.Status.FAILED
        payment.raw_webhook = data
        payment.save(update_fields=['status', 'raw_webhook', 'updated_at'])
        raise ValidationError({'detail': f'Payment not successful ({status or "unknown"}).'})

    amount = from_pesewas(data.get('amount') or 0)
    return fulfill_payment(
        payment=payment,
        provider_payload=data,
        provider_transaction_id=str(data.get('id') or ''),
        amount_ghs=amount,
    )


def verify_platform_payment(*, payment: Payment, actor=None, ip_address: str | None = None) -> Payment:
    """Ask Paystack about a checkout. Complete it only when Paystack says success."""
    from platform_admin.models import PlatformUser
    from platform_admin.services.audit import record_audit

    if payment.provider != Payment.Provider.PAYSTACK:
        raise ValidationError({'detail': 'Only a Paystack payment can be verified.'})
    if payment.status == Payment.Status.SUCCESS:
        return payment

    data = verify_transaction(payment.reference)
    outcome = (data.get('status') or '').lower() or 'unknown'
    if outcome != 'success':
        record_audit(
            actor=actor if isinstance(actor, PlatformUser) else None,
            action='billing.payment.verified',
            target_type='school',
            target_id=str(payment.school_id),
            detail={
                'payment_id': str(payment.pk),
                'reference': payment.reference,
                'outcome': outcome,
                'amount_ghs': f'{payment.amount_ghs:.2f}',
            },
            ip_address=ip_address,
        )
        raise ValidationError({
            'detail': f'Paystack has not confirmed this payment ({outcome}).',
        })

    amount = from_pesewas(data.get('amount') or 0)
    payment = fulfill_payment(
        payment=payment,
        provider_payload=data,
        provider_transaction_id=str(data.get('id') or ''),
        amount_ghs=amount,
    )
    record_audit(
        actor=actor if isinstance(actor, PlatformUser) else None,
        action='billing.payment.verified',
        target_type='school',
        target_id=str(payment.school_id),
        detail={
            'payment_id': str(payment.pk),
            'reference': payment.reference,
            'outcome': 'success',
            'amount_ghs': f'{payment.amount_ghs:.2f}',
        },
        ip_address=ip_address,
    )
    return payment


@transaction.atomic
def handle_paystack_webhook_event(event: dict) -> Payment | None:
    event_name = (event.get('event') or '').strip()
    data = event.get('data') or {}
    if event_name != 'charge.success':
        return None

    reference = (data.get('reference') or '').strip()
    if not reference:
        raise ValidationError({'detail': 'Webhook missing reference.'})

    payment = (
        Payment.objects.select_for_update(of=('self',))
        .select_related('invoice', 'school')
        .filter(reference=reference)
        .first()
    )
    if payment is None:
        # Unknown reference — ignore quietly so Paystack does not retry forever
        # for non-SaaS events on a shared webhook (if misconfigured).
        return None
    if payment.status == Payment.Status.SUCCESS:
        return payment

    amount = from_pesewas(data.get('amount') or 0)
    return fulfill_payment(
        payment=payment,
        provider_payload=event,
        provider_transaction_id=str(data.get('id') or ''),
        amount_ghs=amount,
    )
