import { apiFetch } from './client'

export const settleReceipts = (receipt_ids: number[]) =>
  apiFetch<{ settled: number }>('/settle', {
    method: 'POST',
    body: JSON.stringify({ receipt_ids }),
  })
