import { apiFetch } from './client'
import type { Allocation, SplitType } from '../types'

export interface ParticipantInput {
  user_id: number
  value?: number | null
}

export interface SetAllocationsInput {
  split_type: SplitType
  participants: ParticipantInput[]
}

export const getAllocations = (receiptId: number, itemId: number) =>
  apiFetch<Allocation[]>(`/receipts/${receiptId}/items/${itemId}/allocations`)

export const setAllocations = (
  receiptId: number,
  itemId: number,
  body: SetAllocationsInput,
) =>
  apiFetch<Allocation[]>(`/receipts/${receiptId}/items/${itemId}/allocations`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
