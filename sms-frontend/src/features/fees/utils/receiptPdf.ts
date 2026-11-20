export const openReceiptPdf = (url: string) => {
  const opened = window.open(url, '_blank', 'noopener,noreferrer')
  if (!opened) {
    throw new Error('Pop-up blocked. Allow pop-ups to open the receipt.')
  }
}
