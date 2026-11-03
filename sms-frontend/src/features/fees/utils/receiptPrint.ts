import dayjs from '@/lib/dayjs'
import type { ReceiptDetail } from '../types'
import { formatFeeAmount } from '../utils'

const escapeHtml = (value: string) =>
  value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')

const formatReceiptDateTime = (value: string) => {
  const date = dayjs(value)
  return date.isValid() ? date.format('DD MMM YYYY, HH:mm') : value
}

export const buildReceiptPrintHtml = (receipt: ReceiptDetail) => {
  const addressHtml = receipt.school_address
    ? `${escapeHtml(receipt.school_address)}<br>`
    : ''
  const contactLine = [receipt.school_phone, receipt.school_email]
    .filter((value): value is string => Boolean(value))
    .map(escapeHtml)
    .join(' · ')

  const logoHtml = receipt.school_logo_url
    ? `<img class="logo" src="${escapeHtml(receipt.school_logo_url)}" alt="${escapeHtml(receipt.school_name)} logo" />`
    : ''

  const allocationsHtml =
    receipt.allocations.length > 1
      ? `
        <dt>Applied to</dt>
        <dd>
          ${receipt.allocations
            .map(
              (row) =>
                `${escapeHtml(row.term_label)}: ${escapeHtml(formatFeeAmount(row.amount))}`,
            )
            .join('<br>')}
        </dd>`
      : ''

  const referenceHtml = receipt.payment_reference
    ? `
        <dt>Reference</dt>
        <dd>${escapeHtml(receipt.payment_reference)}</dd>`
    : ''

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Receipt ${escapeHtml(receipt.receipt_number)}</title>
  <style>
    :root { color-scheme: light; }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 32px 16px;
      background: #ffffff;
      color: #0f172a;
      font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
    .sheet {
      max-width: 560px;
      margin: 0 auto;
      background: #ffffff;
    }
    .inner {
      padding: 8px 4px 24px;
    }
    .header {
      display: flex;
      align-items: flex-start;
      gap: 16px;
    }
    .logo {
      display: block;
      width: auto;
      max-width: 140px;
      max-height: 56px;
      object-fit: contain;
      flex-shrink: 0;
    }
    .header-text {
      min-width: 0;
    }
    h1 {
      margin: 0;
      font-size: 22px;
      font-weight: 600;
      letter-spacing: -0.02em;
      color: #0f172a;
    }
    .muted {
      margin: 4px 0 0;
      color: #64748b;
      font-size: 14px;
      line-height: 1.55;
    }
    .amount {
      margin: 24px 0 0;
      font-size: 32px;
      font-weight: 700;
      letter-spacing: -0.03em;
      color: #0f172a;
    }
    .caption {
      margin: 8px 0 24px;
      color: #64748b;
      font-size: 14px;
    }
    dl {
      margin: 0;
      display: grid;
      grid-template-columns: 140px 1fr;
      gap: 10px 16px;
      font-size: 14px;
    }
    dt { color: #64748b; }
    dd {
      margin: 0;
      font-weight: 500;
      color: #0f172a;
    }
    .actions {
      margin: 24px auto 0;
      max-width: 560px;
      text-align: center;
    }
    .actions button {
      border: 0;
      border-radius: 8px;
      background: #0369a1;
      color: #fff;
      padding: 10px 16px;
      font-size: 14px;
      cursor: pointer;
    }
    @media print {
      @page { margin: 12mm; size: auto; }
      body { background: #ffffff; padding: 0; }
      .actions { display: none !important; }
      .sheet { max-width: none; }
    }
  </style>
</head>
<body>
  <div class="sheet">
    <div class="inner">
      <div class="header">
        ${logoHtml}
        <div class="header-text">
          <h1>${escapeHtml(receipt.school_name)}</h1>
          <p class="muted">${addressHtml}${contactLine}</p>
        </div>
      </div>
      <p class="amount">${escapeHtml(formatFeeAmount(receipt.amount))}</p>
      <p class="caption">Payment received</p>
      <dl>
        <dt>Receipt</dt>
        <dd>${escapeHtml(receipt.receipt_number)}</dd>
        <dt>Student</dt>
        <dd>${escapeHtml(receipt.student_name)} (${escapeHtml(receipt.student_id)})</dd>
        <dt>Term</dt>
        <dd>${escapeHtml(receipt.term_label)}</dd>
        ${allocationsHtml}
        <dt>Method</dt>
        <dd>${escapeHtml(receipt.payment_method)}</dd>
        ${referenceHtml}
        <dt>Paid at</dt>
        <dd>${escapeHtml(formatReceiptDateTime(receipt.paid_at))}</dd>
        <dt>Issued</dt>
        <dd>${escapeHtml(formatReceiptDateTime(receipt.issued_at))}</dd>
      </dl>
    </div>
  </div>
  <div class="actions">
    <button type="button" onclick="window.print()">Print / save as PDF</button>
  </div>
</body>
</html>`
}

export const openReceiptPrintWindow = (receipt: ReceiptDetail) => {
  const html = buildReceiptPrintHtml(receipt)
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const printWindow = window.open(url, '_blank')

  if (!printWindow) {
    URL.revokeObjectURL(url)
    throw new Error('Pop-up blocked. Allow pop-ups to print the receipt.')
  }

  let printed = false
  const triggerPrint = () => {
    if (printed) return
    printed = true
    try {
      printWindow.focus()
      printWindow.print()
    } finally {
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
    }
  }

  printWindow.addEventListener('load', () => {
    window.setTimeout(triggerPrint, 100)
  })

  window.setTimeout(() => {
    try {
      if (printWindow.document?.readyState === 'complete') {
        triggerPrint()
      }
    } catch {
      // User can still use the on-page print button.
    }
  }, 400)
}
