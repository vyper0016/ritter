import { apiFetch } from './client'

export interface ReceiptPreview {
  id: number
  vendor_name: string | null
  date: string | null
  total: number | null
  line_items_total: number
  payer_id: number
  per_user: Record<number, number>
  ocr_mismatch: boolean
}

export interface SettlePreview {
  receipts: ReceiptPreview[]
  grand_totals: { user_id: number; payer_id: number; grand_total: number }[]
  any_ocr_mismatch: boolean
}

export const getSettlePreview = () => apiFetch<SettlePreview>('/settle/preview')

export const settleReceipts = (receipt_ids: number[]) =>
  apiFetch<{ settled: number }>('/settle', {
    method: 'POST',
    body: JSON.stringify({ receipt_ids }),
  })

export const unsettleReceipts = (receipt_ids: number[]) =>
  apiFetch<{ unsettled: number }>('/settle/unsettle', {
    method: 'POST',
    body: JSON.stringify({ receipt_ids }),
  })
