import { apiFetch } from './client'
import type { SettlePreview } from '../types'

export const getSettlePreview = () => apiFetch<SettlePreview>('/settle/preview')

export const settleReceipts = (receipt_ids: number[]) =>
  apiFetch<{ settled: number }>('/settle', { method: 'POST', body: JSON.stringify({ receipt_ids }) })

export const settleAll = () =>
  apiFetch<{ settled: number }>('/settle/all', { method: 'POST' })
