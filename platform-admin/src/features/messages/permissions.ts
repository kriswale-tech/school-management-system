import { useAuthStore } from '@/features/auth/store'
import type { PlatformRole } from '@/features/auth/types'

/**
 * Client mirror of the §2.17 permission matrix. This hides affordances only —
 * `HasPlatformRole` on the server remains the enforcement point.
 */
export type MessagesCapability =
  /** See the Messages section at all. Curriculum never does. */
  | 'messages.view'
  /** Create a new SMS/email pricing version. */
  | 'pricing.write'
  /** See provider purchase and expense records (cash paid to providers). */
  | 'providers.cash.view'
  /** Record a manual purchase or expense. */
  | 'providers.cash.write'
  /** Trigger an on-demand provider sync. */
  | 'providers.sync'
  /** Create or edit a MessagingAllowancePolicy. */
  | 'allowances.write'
  /** See the profitability area at all. */
  | 'profitability.view'
  /** See money on the profitability area; Operations gets volumes only. */
  | 'profitability.money'
  /** Start a reconciliation run. */
  | 'reconciliation.trigger'
  /** Close out an open reconciliation item. */
  | 'reconciliation.resolve'
  /** Generate CSV/XLSX exports. */
  | 'exports'

const MATRIX: Record<PlatformRole, MessagesCapability[]> = {
  super_admin: [
    'messages.view',
    'pricing.write',
    'providers.cash.view',
    'providers.cash.write',
    'providers.sync',
    'allowances.write',
    'profitability.view',
    'profitability.money',
    'reconciliation.trigger',
    'reconciliation.resolve',
    'exports',
  ],
  finance: [
    'messages.view',
    'pricing.write',
    'providers.cash.view',
    'providers.cash.write',
    'profitability.view',
    'profitability.money',
    'reconciliation.resolve',
    'exports',
  ],
  operations: [
    'messages.view',
    'providers.cash.view',
    'providers.sync',
    'allowances.write',
    'profitability.view',
    'reconciliation.trigger',
    'exports',
  ],
  // Support is strictly read-only across every Messages surface, and has no
  // access to provider cash records or profitability.
  support: ['messages.view'],
  curriculum: [],
}

export function roleCan(role: PlatformRole | undefined, capability: MessagesCapability) {
  if (!role) return false
  return MATRIX[role]?.includes(capability) ?? false
}

export function useMessagesAccess() {
  const role = useAuthStore((s) => s.user?.role)
  return {
    role,
    can: (capability: MessagesCapability) => roleCan(role, capability),
  }
}
