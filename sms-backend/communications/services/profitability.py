"""Messaging P&L — cash view and usage view, always reported separately (§2.15).

Rules enforced here:
  * cash and usage are never blended into one "profit" number
  * unused credits are never counted as consumed revenue
  * a top-up is never double counted (cash now, usage revenue later)
  * a provider wallet purchase is never treated as the cost of past sends
  * historical snapshots price the usage view — never today's config
  * every estimated figure is labelled
"""

from __future__ import annotations

from decimal import Decimal

from communications.models import Provider
from communications.services.aggregates import (
    EMAIL,
    SMS,
    classification_breakdown,
    comms_cash_from_schools,
    delivery_usage_metrics,
    guardian_deliveries,
    ledger_unit_metrics,
    platform_outbound_metrics,
    provider_expense_metrics,
    provider_purchase_metrics,
    school_balances,
)
from communications.services.ranges import DateRange

MONEY = Decimal('0.01')
UNIT = Decimal('0.000001')
PROVIDER_BY_CHANNEL = {SMS: Provider.ARKESEL, EMAIL: Provider.RESEND}


def _money(value) -> str:
    return str(Decimal(value or 0).quantize(MONEY))


def _unit(value) -> str:
    return str(Decimal(value or 0).quantize(UNIT))


def _margin_pct(profit: Decimal, revenue: Decimal) -> str | None:
    if revenue == 0:
        return None
    return str((profit / revenue * Decimal('100')).quantize(Decimal('0.01')))


def _net_paid_value(*, start, end, channel: str, school=None) -> dict:
    """Usage-valued revenue for PAID traffic, net of reversals.

    Revenue follows the ledger (charged − refunded) so a refunded failure costs
    us provider units without crediting revenue.
    """
    paid = guardian_deliveries(
        start=start,
        end=end,
        channel=channel,
        classification='paid',
        school=school,
    )
    metrics = delivery_usage_metrics(paid, channel=channel)
    charged = metrics['credits_charged']
    refunded = metrics['credits_refunded']
    net_units = max(0, charged - refunded)

    gross_value = Decimal(metrics['usage_valued_revenue_ghs'])
    # Pro-rate the snapshot sell value down to net billed units.
    if charged > 0 and net_units != charged:
        net_value = gross_value * Decimal(net_units) / Decimal(charged)
    else:
        net_value = gross_value
    return {
        'metrics': metrics,
        'net_units': net_units,
        'net_usage_valued_revenue_ghs': net_value,
    }


def channel_profitability(*, date_range: DateRange, channel: str, school=None) -> dict:
    start, end = date_range.start, date_range.end
    provider = PROVIDER_BY_CHANNEL[channel]

    paid = _net_paid_value(start=start, end=end, channel=channel, school=school)
    paid_metrics = paid['metrics']
    paid_cost = Decimal(paid_metrics['provider_cost_ghs'])
    paid_revenue = Decimal(paid['net_usage_valued_revenue_ghs'])
    gross_profit = paid_revenue - paid_cost

    split = classification_breakdown(start=start, end=end, channel=channel, school=school)
    free_cost = Decimal(split['free']['provider_cost_ghs'])
    sponsored_cost = Decimal(split['sponsored']['provider_cost_ghs'])

    platform_funded = platform_outbound_metrics(start=start, end=end, channel=channel)
    platform_cost = Decimal(platform_funded['provider_cost_ghs'])

    cash = comms_cash_from_schools(start=start, end=end, school=school)
    cash_in = Decimal(cash['sms_cash_ghs'] if channel == SMS else cash['email_cash_ghs'])

    purchases = provider_purchase_metrics(start=start, end=end, provider=provider)
    expenses = provider_expense_metrics(start=start, end=end, provider=provider)
    cash_out = Decimal(purchases['amount_ghs']) + Decimal(expenses['amount_ghs'])

    ledger = ledger_unit_metrics(start=start, end=end, channel=channel, school=school)
    balances = school_balances(channel=channel, school=school)

    free_sponsored_expense = free_cost + sponsored_cost
    contribution = gross_profit - free_sponsored_expense

    estimated_flags = {
        'provider_cost_is_estimated': channel == EMAIL,
        'free_sponsored_expense_is_estimated': channel == EMAIL,
    }

    return {
        'channel': channel,
        'cash_view': {
            'cash_received_from_schools_ghs': _money(cash_in),
            'cash_paid_to_providers_ghs': _money(cash_out),
            'provider_purchases_ghs': _money(purchases['amount_ghs']),
            'provider_subscription_ghs': _money(expenses['subscription_ghs']),
            'provider_overage_ghs': _money(expenses['overage_ghs']),
            'provider_other_ghs': _money(expenses['other_ghs']),
            'net_cash_ghs': _money(cash_in - cash_out),
            'note': (
                'Cash movements only. Not profit — unused credits sold here are '
                'still a liability to deliver.'
            ),
        },
        'usage_view': {
            'paid_units_consumed': paid['net_units'],
            'paid_units_charged': paid_metrics['credits_charged'],
            'paid_units_refunded': paid_metrics['credits_refunded'],
            'usage_valued_revenue_ghs': _unit(paid_revenue),
            'provider_cost_ghs': _unit(paid_cost),
            'gross_profit_ghs': _unit(gross_profit),
            'gross_margin_pct': _margin_pct(gross_profit, paid_revenue),
            'free_units': split['free']['units'],
            'free_expense_ghs': _unit(free_cost),
            'sponsored_units': split['sponsored']['units'],
            'sponsored_expense_ghs': _unit(sponsored_cost),
            'free_sponsored_expense_ghs': _unit(free_sponsored_expense),
            'platform_funded_units': (
                platform_funded['sms_segments']
                if channel == SMS
                else platform_funded['email_messages']
            ),
            'platform_funded_expense_ghs': _unit(platform_cost),
            'contribution_ghs': _unit(contribution),
            'unpriced_rows': paid_metrics['unpriced_rows'],
            'unpriced_note': (
                'Pre-v4.1 deliveries carry no cost snapshots and are excluded '
                'from valuation rather than re-priced with today’s config.'
            ),
            **estimated_flags,
        },
        'credits_view': {
            **ledger,
            'remaining_units': balances.get(channel, 0),
            'note': 'Remaining credits are a delivery liability, not revenue.',
        },
    }


def messaging_profitability(
    *,
    date_range: DateRange,
    channel: str | None = None,
    view: str | None = None,
    school=None,
    volumes_only: bool = False,
) -> dict:
    """Combined P&L. ``view`` may narrow to ``cash`` or ``usage``, never merge them."""
    channels = [channel] if channel in (SMS, EMAIL) else [SMS, EMAIL]
    blocks = {
        key: channel_profitability(date_range=date_range, channel=key, school=school)
        for key in channels
    }

    total_cash_in = sum(
        (Decimal(block['cash_view']['cash_received_from_schools_ghs']) for block in blocks.values()),
        Decimal('0'),
    )
    total_cash_out = sum(
        (Decimal(block['cash_view']['cash_paid_to_providers_ghs']) for block in blocks.values()),
        Decimal('0'),
    )
    total_revenue = sum(
        (Decimal(block['usage_view']['usage_valued_revenue_ghs']) for block in blocks.values()),
        Decimal('0'),
    )
    total_cost = sum(
        (Decimal(block['usage_view']['provider_cost_ghs']) for block in blocks.values()),
        Decimal('0'),
    )
    total_free_sponsored = sum(
        (Decimal(block['usage_view']['free_sponsored_expense_ghs']) for block in blocks.values()),
        Decimal('0'),
    )
    total_platform_funded = sum(
        (
            Decimal(block['usage_view']['platform_funded_expense_ghs'])
            for block in blocks.values()
        ),
        Decimal('0'),
    )
    gross_profit = total_revenue - total_cost

    combined = {
        'cash_view': {
            'cash_received_from_schools_ghs': _money(total_cash_in),
            'cash_paid_to_providers_ghs': _money(total_cash_out),
            'net_cash_ghs': _money(total_cash_in - total_cash_out),
        },
        'usage_view': {
            'usage_valued_revenue_ghs': _unit(total_revenue),
            'provider_cost_ghs': _unit(total_cost),
            'gross_profit_ghs': _unit(gross_profit),
            'gross_margin_pct': _margin_pct(gross_profit, total_revenue),
            'free_sponsored_expense_ghs': _unit(total_free_sponsored),
            'platform_funded_expense_ghs': _unit(total_platform_funded),
            'overall_contribution_ghs': _unit(gross_profit - total_free_sponsored),
            'email_provider_cost_is_estimated': True,
        },
    }

    if volumes_only:
        # Operations role: volumes without money (v4.1 §2.17).
        return {
            'range': date_range.as_dict(),
            'view': 'volumes',
            'channels': {
                key: {
                    'channel': key,
                    'paid_units_consumed': block['usage_view']['paid_units_consumed'],
                    'free_units': block['usage_view']['free_units'],
                    'sponsored_units': block['usage_view']['sponsored_units'],
                    'platform_funded_units': block['usage_view']['platform_funded_units'],
                    'credits_view': {
                        'allocated_units': block['credits_view']['allocated_units'],
                        'consumed_units': block['credits_view']['consumed_units'],
                        'remaining_units': block['credits_view']['remaining_units'],
                    },
                }
                for key, block in blocks.items()
            },
            'note': 'Financial figures are restricted for this role.',
        }

    if view in ('cash', 'usage'):
        key = f'{view}_view'
        return {
            'range': date_range.as_dict(),
            'view': view,
            'channels': {
                channel_key: {
                    'channel': channel_key,
                    key: block[key],
                }
                for channel_key, block in blocks.items()
            },
            'combined': {key: combined[key]},
            'note': 'Cash and usage views are never blended into one profit number.',
        }

    return {
        'range': date_range.as_dict(),
        'view': 'both',
        'channels': blocks,
        'combined': combined,
        'note': 'Cash and usage views are reported separately by design.',
    }
