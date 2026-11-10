"""Platform-wide messaging overview (v4.1 §2.4 area 1, §2.5).

Every tile is tagged with the money layer it belongs to. No figure in this
payload mixes provider balance, school balance, cash, and usage value.
"""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Count

from communications.models import (
    MessagingAllowancePolicy,
    Provider,
    ProviderAccount,
    ProviderReconciliationItem,
    ProviderReconciliationRun,
)
from communications.services.aggregates import (
    EMAIL,
    SMS,
    classification_breakdown,
    comms_cash_from_schools,
    delivery_status_counts,
    delivery_usage_metrics,
    guardian_deliveries,
    latest_provider_balance,
    latest_resend_usage,
    ledger_unit_metrics,
    platform_outbound_metrics,
    provider_expense_metrics,
    provider_purchase_metrics,
    school_balances,
    unpaid_comms_invoice_total,
)
from communications.services.pricing import get_active_email_config, get_active_sms_configs
from communications.services.ranges import DateRange


def _decimal_str(value) -> str:
    return str(Decimal(value or 0).quantize(Decimal('0.000001')))


def _money_str(value) -> str:
    return str(Decimal(value or 0).quantize(Decimal('0.01')))


def _channel_block(*, date_range: DateRange, channel: str, school=None) -> dict:
    accepted = guardian_deliveries(
        start=date_range.start,
        end=date_range.end,
        channel=channel,
        school=school,
    )
    everything = guardian_deliveries(
        start=date_range.start,
        end=date_range.end,
        channel=channel,
        school=school,
        accepted_only=False,
    )
    usage = delivery_usage_metrics(accepted, channel=channel)
    statuses = delivery_status_counts(everything)
    ledger = ledger_unit_metrics(
        start=date_range.start,
        end=date_range.end,
        channel=channel,
        school=school,
    )
    split = classification_breakdown(
        start=date_range.start,
        end=date_range.end,
        channel=channel,
        school=school,
    )
    balances = school_balances(channel=channel, school=school)

    return {
        'channel': channel,
        'layer_5_usage': {
            'messages': usage['messages'],
            'segments': usage['segments'],
            'units_consumed': usage['units'],
            'credits_charged': usage['credits_charged'],
            'credits_refunded': usage['credits_refunded'],
            'provider_cost_ghs': _decimal_str(usage['provider_cost_ghs']),
            'provider_cost_is_estimated': channel == EMAIL,
            'usage_valued_revenue_ghs': _decimal_str(usage['usage_valued_revenue_ghs']),
            'unpriced_rows': usage['unpriced_rows'],
            'unbilled_rows': usage['unbilled_rows'],
        },
        'delivery_statuses': statuses,
        'layer_2_school_credits': {
            **ledger,
            'remaining_units': balances.get(channel, 0),
            'remaining_units_note': (
                'Unused credits are a delivery liability, not consumed revenue.'
            ),
        },
        'classification': {
            key: {
                'messages': value['messages'],
                'units': value['units'],
                'provider_cost_ghs': _decimal_str(value['provider_cost_ghs']),
            }
            for key, value in split.items()
        },
    }


def _provider_block(*, date_range: DateRange) -> dict:
    arkesel_purchases = provider_purchase_metrics(
        start=date_range.start,
        end=date_range.end,
        provider=Provider.ARKESEL,
    )
    ses_expenses = provider_expense_metrics(
        start=date_range.start,
        end=date_range.end,
        provider=Provider.SES,
    )
    # Include legacy Resend expenses if any remain in history.
    legacy_resend_expenses = provider_expense_metrics(
        start=date_range.start,
        end=date_range.end,
        provider=Provider.RESEND,
    )
    all_purchases = provider_purchase_metrics(start=date_range.start, end=date_range.end)
    all_expenses = provider_expense_metrics(start=date_range.start, end=date_range.end)

    accounts = [
        {
            'provider': account.provider,
            'channel': account.channel,
            'display_name': account.display_name,
            'api_status': account.api_status,
            'last_synced_at': account.last_synced_at,
            'last_error': account.last_error,
            'last_webhook_at': account.last_webhook_at,
            'webhook_signature_failures': account.webhook_signature_failures,
        }
        for account in ProviderAccount.objects.all()
    ]

    return {
        'accounts': accounts,
        'layer_1_provider_wallet': {
            'arkesel_balance': latest_provider_balance(),
            'ses_usage': latest_resend_usage(),
            # Alias kept for older frontend readers.
            'resend_usage': latest_resend_usage(),
            'note': (
                'A provider wallet purchase is cash out, not the cost of '
                'messages already sent. SES has no prepaid wallet — usage is '
                'pay-per-send (plus optional AWS monitoring costs).'
            ),
        },
        'layer_4_cash_to_providers': {
            'arkesel_purchases_ghs': _money_str(arkesel_purchases['amount_ghs']),
            'arkesel_units_purchased': arkesel_purchases['units_purchased'],
            'arkesel_blended_cost_per_unit_ghs': (
                _decimal_str(arkesel_purchases['blended_cost_per_unit_ghs'])
                if arkesel_purchases['blended_cost_per_unit_ghs'] is not None
                else None
            ),
            'ses_expenses_ghs': _money_str(ses_expenses['amount_ghs']),
            'ses_subscription_ghs': _money_str(ses_expenses['subscription_ghs']),
            'ses_overage_ghs': _money_str(ses_expenses['overage_ghs']),
            'resend_subscription_ghs': _money_str(legacy_resend_expenses['subscription_ghs']),
            'resend_overage_ghs': _money_str(legacy_resend_expenses['overage_ghs']),
            'total_purchases_ghs': _money_str(all_purchases['amount_ghs']),
            'total_expenses_ghs': _money_str(all_expenses['amount_ghs']),
            'total_ghs': _money_str(
                Decimal(all_purchases['amount_ghs']) + Decimal(all_expenses['amount_ghs']),
            ),
        },
    }


def _pricing_block() -> dict:
    sms_configs = get_active_sms_configs()
    email_config = get_active_email_config()
    return {
        'sms': {
            encoding: {
                'provider_cost_per_segment_ghs': _decimal_str(
                    config.provider_cost_per_segment_ghs,
                ),
                'school_price_per_segment_ghs': _decimal_str(
                    config.school_price_per_segment_ghs,
                ),
                'single_segment_limit': config.single_segment_limit,
                'multipart_segment_limit': config.multipart_segment_limit,
                'effective_from': config.effective_from,
            }
            for encoding, config in sms_configs.items()
        },
        'email': (
            {
                'school_price_per_credit_ghs': _decimal_str(
                    email_config.school_price_per_credit_ghs,
                ),
                'estimated_provider_cost_per_email_ghs': _decimal_str(
                    email_config.estimated_provider_cost_per_email_ghs,
                ),
                'provider_cost_is_estimated': True,
                'billing_unit': email_config.billing_unit,
                'effective_from': email_config.effective_from,
            }
            if email_config is not None
            else None
        ),
        'unit_price_note': (
            'Unit prices are economics reference values only. Nothing is billed '
            'in GHS at send time; metering stays in credits.'
        ),
    }


def _operations_block() -> dict:
    open_items = (
        ProviderReconciliationItem.objects.filter(
            resolution=ProviderReconciliationItem.Resolution.OPEN,
        )
        .values('discrepancy_type')
        .annotate(count=Count('id'))
    )
    last_runs = {}
    for run in ProviderReconciliationRun.objects.order_by('provider', '-started_at'):
        last_runs.setdefault(
            run.provider,
            {
                'id': str(run.pk),
                'status': run.status,
                'started_at': run.started_at,
                'finished_at': run.finished_at,
                'discrepancy_count': run.discrepancy_count,
            },
        )
    return {
        'open_reconciliation_items': {
            row['discrepancy_type']: int(row['count'] or 0) for row in open_items
        },
        'open_reconciliation_total': sum(int(row['count'] or 0) for row in open_items),
        'last_reconciliation_run': last_runs,
        'active_allowance_policies': MessagingAllowancePolicy.objects.filter(
            is_active=True,
        ).count(),
    }


def messaging_overview(
    *,
    date_range: DateRange,
    school=None,
    channel: str | None = None,
    classification: str | None = None,
) -> dict:
    """Assemble the platform Messages overview for one window."""
    channels = [channel] if channel in (SMS, EMAIL) else [SMS, EMAIL]
    channel_blocks = {
        key: _channel_block(date_range=date_range, channel=key, school=school)
        for key in channels
    }

    if classification:
        for block in channel_blocks.values():
            block['classification_filter'] = classification
            filtered = guardian_deliveries(
                start=date_range.start,
                end=date_range.end,
                channel=block['channel'],
                classification=classification,
                school=school,
            )
            metrics = delivery_usage_metrics(filtered, channel=block['channel'])
            block['filtered_usage'] = {
                'messages': metrics['messages'],
                'units': metrics['units'],
                'provider_cost_ghs': _decimal_str(metrics['provider_cost_ghs']),
            }

    cash = comms_cash_from_schools(start=date_range.start, end=date_range.end, school=school)
    platform_funded = platform_outbound_metrics(start=date_range.start, end=date_range.end)

    return {
        'range': date_range.as_dict(),
        'filters': {
            'school': str(school.pk) if school is not None else None,
            'channel': channel or None,
            'classification': classification or None,
        },
        'channels': channel_blocks,
        'layer_3_cash_from_schools': {
            'topup_cash_ghs': _money_str(cash['topup_cash_ghs']),
            'addon_cash_ghs': _money_str(cash['addon_cash_ghs']),
            'total_cash_ghs': _money_str(cash['total_cash_ghs']),
            'sms_cash_ghs': _money_str(cash['sms_cash_ghs']),
            'email_cash_ghs': _money_str(cash['email_cash_ghs']),
            'unpaid_addon_invoiced_ghs': _money_str(
                unpaid_comms_invoice_total(start=date_range.start, end=date_range.end),
            ),
            'note': (
                'A credit sold is cash received and a liability to deliver — it '
                'becomes usage revenue only when consumed.'
            ),
        },
        'platform_funded': {
            **{
                key: value
                for key, value in platform_funded.items()
                if key != 'provider_cost_ghs'
            },
            'provider_cost_ghs': _decimal_str(platform_funded['provider_cost_ghs']),
            'note': (
                'OTP and staff email are platform funded and never debit a '
                'school ledger (v4 invariant 4).'
            ),
        },
        'providers': _provider_block(date_range=date_range),
        'pricing': _pricing_block(),
        'operations': _operations_block(),
        'layer_warning': (
            'Provider balance, school credits, cash, and usage value are '
            'different layers. Never sum across them.'
        ),
    }
