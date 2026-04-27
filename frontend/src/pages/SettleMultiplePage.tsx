import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useQueries, useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getItems, getReceipt, getReceiptSummary } from '../api/receipts'
import { getSettlePreview, settleReceipts, unsettleReceipts } from '../api/settle'
import { getUsers } from '../api/users'
import ReceiptPanel from '../components/ReceiptPanel'

export default function SettleMultiplePage() {
  const location = useLocation()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const receiptIds: number[] = location.state?.receiptIds ?? []

  const itemsResults = useQueries({
    queries: receiptIds.map((id) => ({
      queryKey: ['items', id],
      queryFn: () => getItems(id),
    })),
  })

  const receiptResults = useQueries({
    queries: receiptIds.map((id) => ({
      queryKey: ['receipt', id],
      queryFn: () => getReceipt(id),
    })),
  })

  const { data: preview } = useQuery({ queryKey: ['settle-preview'], queryFn: getSettlePreview })
  const { data: users } = useQuery({ queryKey: ['users'], queryFn: getUsers })

  const receipts = receiptResults.map((r) => r.data)
  const allSettled = receipts.length > 0 && receipts.every((r) => r?.settled)

  const summaryResults = useQueries({
    queries: receiptIds.map((id, idx) => ({
      queryKey: ['receipt-summary', id],
      queryFn: () => getReceiptSummary(id),
      enabled: !!receipts[idx]?.settled,
    })),
  })

  const settleMutation = useMutation({
    mutationFn: () => settleReceipts(receiptIds),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['receipts'] })
      qc.invalidateQueries({ queryKey: ['receipt'] })
      qc.invalidateQueries({ queryKey: ['settle-preview'] })
      navigate('/')
    },
  })

  const unsettleMutation = useMutation({
    mutationFn: () => unsettleReceipts(receiptIds),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['receipts'] })
      qc.invalidateQueries({ queryKey: ['receipt'] })
      qc.invalidateQueries({ queryKey: ['settle-preview'] })
    },
  })

  useEffect(() => {
    if (receiptIds.length === 0) navigate('/', { replace: true })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  if (receiptIds.length === 0) return null

  const subtotals = itemsResults.map(
    (q) => q.data?.reduce((s, i) => s + i.total, 0) ?? 0,
  )
  const grandTotal = subtotals.reduce((s, v) => s + v, 0)

  // Build per-participant breakdown
  const selectedSet = new Set(receiptIds)
  const owedMap = new Map<string, { userId: number; payerId: number; amount: number }>()

  // Unsettled: from preview
  if (preview) {
    for (const r of preview.receipts) {
      if (!selectedSet.has(r.id)) continue
      for (const [userIdStr, amount] of Object.entries(r.per_user)) {
        const userId = Number(userIdStr)
        if (userId === r.payer_id) continue
        const key = `${userId}->${r.payer_id}`
        const existing = owedMap.get(key)
        if (existing) existing.amount += amount
        else owedMap.set(key, { userId, payerId: r.payer_id, amount })
      }
    }
  }

  // Settled: from per-receipt summary
  receiptIds.forEach((_id, idx) => {
    const receipt = receipts[idx]
    if (!receipt?.settled) return
    const summary = summaryResults[idx]?.data
    if (!summary) return
    for (const { user_id, total_owed } of summary) {
      if (user_id === receipt.payer_id) continue
      const key = `${user_id}->${receipt.payer_id}`
      const existing = owedMap.get(key)
      if (existing) existing.amount += total_owed
      else owedMap.set(key, { userId: user_id, payerId: receipt.payer_id, amount: total_owed })
    }
  })

  // Net out reciprocal debts: if A owes B x and B owes A y, keep only difference.
  const netMap = new Map<string, { userId: number; payerId: number; amount: number }>()
  for (const { userId, payerId, amount } of owedMap.values()) {
    const pairKey = userId < payerId ? `${userId}|${payerId}` : `${payerId}|${userId}`
    const existing = netMap.get(pairKey)
    if (!existing) {
      netMap.set(pairKey, { userId, payerId, amount })
    } else if (existing.userId === userId && existing.payerId === payerId) {
      existing.amount += amount
    } else {
      const diff = existing.amount - amount
      if (diff > 0) existing.amount = diff
      else if (diff < 0) {
        existing.userId = userId
        existing.payerId = payerId
        existing.amount = -diff
      } else netMap.delete(pairKey)
    }
  }

  const owedEntries = [...netMap.values()]
    .filter((e) => e.amount > 0.005)
    .sort((a, b) => b.amount - a.amount)

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-800">
          {allSettled ? 'Settled' : 'Settle'} {receiptIds.length} Receipt{receiptIds.length !== 1 ? 's' : ''}
        </h1>
        <button
          onClick={() => navigate(-1)}
          className="text-sm text-gray-500 hover:text-gray-800"
        >
          ← Back
        </button>
      </div>

      <div className="space-y-8">
        {receiptIds.map((id, idx) => (
          <div key={id} className="border-b border-gray-200 pb-6 last:border-0 last:pb-0">
            <ReceiptPanel receiptId={id} onDeleted={() => navigate('/')} />
            <div className="flex justify-end mt-3 text-sm text-gray-600 items-center gap-1.5">
              {(() => {
                const receipt = receipts[idx]
                const mismatch = receipt?.total != null &&
                  !itemsResults[idx].isLoading &&
                  Math.abs(receipt.total - subtotals[idx]) > 0.005
                return mismatch ? (
                  <span title={`OCR total €${receipt!.total!.toFixed(2)} differs from items sum`} className="text-amber-500">⚠</span>
                ) : null
              })()}
              Subtotal:{' '}
              <strong className="ml-1 text-gray-800">
                {itemsResults[idx].isLoading ? '…' : `€${subtotals[idx].toFixed(2)}`}
              </strong>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-sm text-gray-500">Total</p>
            <p className="text-2xl font-bold text-gray-800">€{grandTotal.toFixed(2)}</p>
          </div>
          {allSettled ? (
            <button
              onClick={() => unsettleMutation.mutate()}
              disabled={unsettleMutation.isPending}
              className="bg-gray-600 text-white px-8 py-3 rounded-lg text-sm font-medium hover:bg-gray-700 disabled:opacity-50"
            >
              {unsettleMutation.isPending ? 'Unsettling…' : 'Unsettle'}
            </button>
          ) : (
            <button
              onClick={() => settleMutation.mutate()}
              disabled={settleMutation.isPending}
              className="bg-green-600 text-white px-8 py-3 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            >
              {settleMutation.isPending ? 'Settling…' : 'Settle'}
            </button>
          )}
        </div>
        {owedEntries.length > 0 && (
          <div className="border-t border-gray-100 pt-4 space-y-2">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
              {allSettled ? 'Paid' : 'Who pays whom'}
            </p>
            {owedEntries.map(({ userId, payerId, amount }) => {
              const participant = users?.find((u) => u.id === userId)
              const payer = users?.find((u) => u.id === payerId)
              return (
                <div key={`${userId}-${payerId}`} className="flex items-center justify-between text-sm">
                  <span className="text-gray-700">
                    <span className="font-medium">{participant?.name ?? `User #${userId}`}</span>
                    <span className="text-gray-400 mx-1.5">→</span>
                    <span className="font-medium">{payer?.name ?? `User #${payerId}`}</span>
                  </span>
                  <span className="font-semibold text-gray-800">€{amount.toFixed(2)}</span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
