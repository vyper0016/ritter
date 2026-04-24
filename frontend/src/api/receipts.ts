import { apiFetch } from './client'
import type { Receipt, LineItem } from '../types'

export interface CreateReceiptParams {
  payer_id: number
  participant_ids: number[]
  image?: File
}

export interface ListReceiptsParams {
  settled?: boolean
  role?: 'uploaded' | 'participant' | 'all'
}

export const listReceipts = (params: ListReceiptsParams = {}) => {
  const q = new URLSearchParams()
  if (params.settled !== undefined) q.set('settled', String(params.settled))
  if (params.role) q.set('role', params.role)
  const qs = q.toString()
  return apiFetch<Receipt[]>(`/receipts${qs ? '?' + qs : ''}`)
}

export const getReceipt = (id: number) => apiFetch<Receipt>(`/receipts/${id}`)

export const createReceipt = ({ payer_id, participant_ids, image }: CreateReceiptParams) => {
  const form = new FormData()
  form.append('payer_id', String(payer_id))
  for (const p of participant_ids) form.append('participant_ids', String(p))
  if (image) form.append('image', image)
  return apiFetch<Receipt>('/receipts', { method: 'POST', body: form })
}

export const getItems = (receiptId: number) =>
  apiFetch<LineItem[]>(`/receipts/${receiptId}/items`)

export const addItem = (receiptId: number, data: { description?: string; total: number }) =>
  apiFetch<LineItem>(`/receipts/${receiptId}/items`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const updateItem = (
  receiptId: number,
  itemId: number,
  data: { description?: string; total?: number },
) =>
  apiFetch<LineItem>(`/receipts/${receiptId}/items/${itemId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })

export const deleteItem = (receiptId: number, itemId: number) =>
  apiFetch<void>(`/receipts/${receiptId}/items/${itemId}`, { method: 'DELETE' })
