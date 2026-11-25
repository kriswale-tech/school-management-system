const ACTION_LABELS: Record<string, string> = {
  'messages.arkesel_test.sent': 'Test SMS sent',
  'messages.ses_test.sent': 'Test email sent',
  'messages.provider_purchase.created': 'Provider purchase recorded',
  'messages.provider_expense.created': 'Provider expense recorded',
  'messages.allowance.created': 'Messaging allowance created',
  'messages.allowance.updated': 'Messaging allowance updated',
  'messages.export.generated': 'Messages export generated',
  'messages.sms_pricing.version_created': 'SMS price updated',
  'messages.email_pricing.version_created': 'Email price updated',
  'messages.reconciliation.arkesel_run': 'Arkesel reconciliation run',
  'messages.reconciliation.ses_run': 'SES reconciliation run',
  'messages.reconciliation.item_resolved': 'Reconciliation item resolved',
  'messages.unbilled_send.recorded': 'Unbilled send recorded',
  'platform.school.created': 'School created',
  'platform.school.updated': 'School updated',
  'platform.school.status_changed': 'Status changed',
  'platform.school.invite_sent': 'Admin invite sent',
  'platform.school.invite_resent': 'Admin invite resent',
  'platform.school.invite_accepted': 'Admin invite accepted',
  'platform.curriculum.draft_started': 'Curriculum draft started',
  'platform.curriculum.published': 'Curriculum published',
  'platform.curriculum.adopted': 'Curriculum adopted',
  'platform.auth.login_password': 'Signed in',
  'platform.auth.login_mfa': 'Signed in with a code',
  'platform.auth.logout': 'Signed out',
  'platform.mfa.enabled': 'Multi-factor enabled',
  'platform.mfa.disabled': 'Multi-factor disabled',
  'platform.settings.updated': 'Settings updated',
  'billing.subscription.started': 'Subscription started',
  'billing.subscription.change_scheduled': 'Plan change scheduled',
  'billing.subscription.capacity_upgrade': 'Plan upgraded',
  'billing.subscription.renewed': 'Subscription renewed',
  'billing.topup.recorded_paid': 'Credits added',
  'billing.payment.verified': 'Payment verified',
  'billing.dunning.grace_extended': 'Grace period extended',
  'billing.dunning.school_reactivated': 'School reactivated',
  'billing.dunning.suspended': 'School suspended for non-payment',
  'billing.dunning.grace_reminder': 'Grace reminder sent',
  'billing.discount.created': 'Discount created',
  'billing.discount.updated': 'Discount updated',
  'billing.discount.deleted': 'Discount deleted',
  'billing.discount.assigned': 'Discount assigned',
  'billing.discount.revoked': 'Discount revoked',
  'billing.discount.restored': 'Discount restored',
  'billing.invoice.capacity_upgrade_paid': 'Capacity upgrade paid',
  'billing.invoice.interval_change_paid': 'Billing interval change paid',
  'communications.addon.change_cancelled': 'Add-on change cancelled',
}

export const ACTION_FILTERS = [
  { value: '', label: 'All actions' },
  { value: 'platform.auth', label: 'Sign-ins' },
  { value: 'platform.mfa', label: 'Multi-factor' },
  { value: 'platform.school', label: 'Schools' },
  { value: 'platform.curriculum', label: 'Curriculum' },
  { value: 'platform.settings', label: 'Settings' },
  { value: 'billing', label: 'Billing' },
  { value: 'messages', label: 'Messages' },
  { value: 'communications', label: 'Add-ons' },
]

export const TARGET_FILTERS = [
  { value: '', label: 'All targets' },
  { value: 'school', label: 'School' },
  { value: 'platform_user', label: 'Platform user' },
  { value: 'curriculum', label: 'Curriculum' },
  { value: 'platform_settings', label: 'Settings' },
  { value: 'arkesel_test', label: 'Test SMS' },
  { value: 'ses_test', label: 'Test email' },
  { value: 'provider_purchase', label: 'Provider purchase' },
  { value: 'provider_expense', label: 'Provider expense' },
  { value: 'promotion_campaign', label: 'Discount' },
]

export function actionLabel(action: string) {
  return ACTION_LABELS[action] ?? action.replaceAll('.', ' ').replaceAll('_', ' ')
}

export function auditSummary(detail: Record<string, unknown>) {
  const from = typeof detail.from === 'string' ? detail.from : ''
  const to = typeof detail.to === 'string' ? detail.to : ''
  const reason = typeof detail.reason === 'string' ? detail.reason : ''
  if (from && to && !to.startsWith('+') && !to.startsWith('0')) {
    return reason ? `${from} → ${to} · ${reason}` : `${from} → ${to}`
  }
  const parts: string[] = []
  if (to) parts.push(to)
  if (detail.sandbox === true) parts.push('sandbox')
  if (detail.sandbox === false) parts.push('live')
  if (typeof detail.amount_ghs === 'string' && detail.amount_ghs) parts.push(`GHS ${detail.amount_ghs}`)
  if (typeof detail.subject === 'string' && detail.subject) parts.push(detail.subject)
  if (reason) parts.push(reason)
  return parts.join(' · ')
}

export function detailRows(detail: Record<string, unknown>) {
  return Object.entries(detail).map(([key, value]) => ({
    key: key.replaceAll('_', ' '),
    value: value == null ? '—' : typeof value === 'string' ? value : JSON.stringify(value),
  }))
}
