import { apiFetch } from './client'
import type { Allocation, SplitType } from '../types'

export interface AllocationInput {
  user_id: number
  split_type: SplitType
  split_value?: number | null
}

export const getAllocations = (receiptId: number, itemId: number) =>
  apiFetch<Allocation[]>(`/receipts/${receiptId}/items/${itemId}/allocations`)

export const setAllocations = (
  receiptId: number,
  itemId: number,
  allocations: AllocationInput[],
) =>
  apiFetch<Allocation[]>(`/receipts/${receiptId}/items/${itemId}/allocations`, {
    method: 'PUT',
    body: JSON.stringify(allocations),
  })
