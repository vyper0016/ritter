import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSettlePreview, settleAll, settleReceipts } from '../api/settle'
import { getUsers } from '../api/users'

export default function SettlePage() {
  const qc = useQueryClient()

  const { data: preview, isLoading } = useQuery({
    queryKey: ['settle-preview'],
    queryFn: getSettlePreview,
  })

  const { data: users } = useQuery({ queryKey: ['users'], queryFn: getUsers })

  const settleAllMutation = useMutation({
    mutationFn: settleAll,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['settle-preview'] }),
  })

  const settleOneMutation = useMutation({
    mutationFn: (id: number) => settleReceipts([id]),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['settle-preview'] }),
  })

  function userName(id: number) {
    return users?.find((u) => u.id === id)?.name ?? `#${id}`
  }

  if (isLoading) return <div className="p-8 text-gray-400">Loading…</div>

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-800">Settle</h1>
        <button
          onClick={() => settleAllMutation.mutate()}
          disabled={settleAllMutation.isPending || !preview?.receipts.length}
          className="bg-green-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50"
        >
          {settleAllMutation.isPending ? 'Settling…' : 'Settle all'}
        </button>
      </div>

      {preview?.any_ocr_mismatch && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4 text-sm text-yellow-800">
          ⚠ Some receipts have OCR total mismatches — check line items before settling.
        </div>
      )}

      {preview?.grand_totals && preview.grand_totals.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
          <h2 className="text-sm font-medium text-gray-700 mb-3">Grand Totals</h2>
          <div className="space-y-2">
            {preview.grand_totals.map((gt) => (
              <div key={gt.user_id} className="flex justify-between text-sm">
                <span className="text-gray-600">
                  {userName(gt.user_id)} owes {userName(gt.payer_id)}
                </span>
                <span className="font-semibold text-gray-800">€{gt.grand_total.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {preview?.receipts.length === 0 && (
        <p className="text-gray-400 text-sm">No unsettled receipts.</p>
      )}

      <div className="space-y-3">
        {preview?.receipts.map((r) => (
          <div
            key={r.id}
            className={`bg-white rounded-xl border p-4 ${r.ocr_mismatch ? 'border-yellow-300' : 'border-gray-200'}`}
          >
            <div className="flex items-start justify-between mb-2">
              <div>
                <p className="font-medium text-gray-800">{r.vendor_name ?? 'Receipt #' + r.id}</p>
                {r.ocr_mismatch && (
                  <p className="text-xs text-yellow-600 mt-0.5">
                    OCR mismatch: total €{r.total?.toFixed(2)} vs items €{r.line_items_total.toFixed(2)}
                  </p>
                )}
              </div>
              <button
                onClick={() => settleOneMutation.mutate(r.id)}
                disabled={settleOneMutation.isPending}
                className="text-xs text-green-700 border border-green-300 px-2 py-1 rounded hover:bg-green-50 disabled:opacity-50"
              >
                Settle
              </button>
            </div>
            <div className="flex flex-wrap gap-3 text-xs text-gray-500">
              {Object.entries(r.per_user).map(([uid, amt]) => (
                <span key={uid}>{userName(Number(uid))}: €{(amt as number).toFixed(2)}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
