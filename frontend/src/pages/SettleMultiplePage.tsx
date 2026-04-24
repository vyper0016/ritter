import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useQueries, useMutation, useQueryClient } from '@tanstack/react-query'
import { getItems } from '../api/receipts'
import { settleReceipts } from '../api/settle'
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

  const settleMutation = useMutation({
    mutationFn: () => settleReceipts(receiptIds),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['receipts'] })
      navigate('/')
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

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-800">
          Settle {receiptIds.length} Receipt{receiptIds.length !== 1 ? 's' : ''}
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
            <div className="flex justify-end mt-3 text-sm text-gray-600">
              Subtotal:{' '}
              <strong className="ml-1 text-gray-800">
                {itemsResults[idx].isLoading ? '…' : `€${subtotals[idx].toFixed(2)}`}
              </strong>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500">Total settlement</p>
            <p className="text-2xl font-bold text-gray-800">€{grandTotal.toFixed(2)}</p>
          </div>
          <button
            onClick={() => settleMutation.mutate()}
            disabled={settleMutation.isPending}
            className="bg-green-600 text-white px-8 py-3 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
          >
            {settleMutation.isPending ? 'Settling…' : 'Settle'}
          </button>
        </div>
      </div>
    </div>
  )
}
