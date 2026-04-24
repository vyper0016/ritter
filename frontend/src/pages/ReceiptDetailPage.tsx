import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getReceipt, getItems, addItem, deleteItem } from '../api/receipts'
import { getUsers } from '../api/users'
import OcrBadge from '../components/OcrBadge'
import AllocationEditor from '../components/AllocationEditor'

const POLL_STATUSES = new Set(['pending', 'processing'])

export default function ReceiptDetailPage() {
  const { id } = useParams<{ id: string }>()
  const receiptId = Number(id)
  const qc = useQueryClient()

  const { data: receipt } = useQuery({
    queryKey: ['receipt', receiptId],
    queryFn: () => getReceipt(receiptId),
    refetchInterval: (query) =>
      query.state.data && POLL_STATUSES.has(query.state.data.ocr_status) ? 2000 : false,
  })

  const { data: items } = useQuery({
    queryKey: ['items', receiptId],
    queryFn: () => getItems(receiptId),
  })

  const { data: users } = useQuery({ queryKey: ['users'], queryFn: getUsers })

  const [addDesc, setAddDesc] = useState('')
  const [addTotal, setAddTotal] = useState('')
  const [expandedItem, setExpandedItem] = useState<number | null>(null)

  const addMutation = useMutation({
    mutationFn: () => addItem(receiptId, { description: addDesc || undefined, total: Number(addTotal) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['items', receiptId] })
      setAddDesc('')
      setAddTotal('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (itemId: number) => deleteItem(receiptId, itemId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['items', receiptId] }),
  })

  const participants = users?.filter((u) => receipt?.participant_ids.includes(u.id)) ?? []
  const payer = users?.find((u) => u.id === receipt?.payer_id)

  if (!receipt) return <div className="p-8 text-gray-400">Loading…</div>

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h1 className="text-xl font-semibold text-gray-800">
              {receipt.vendor_name ?? 'Receipt #' + receipt.id}
            </h1>
            {receipt.date && <p className="text-sm text-gray-500 mt-0.5">{receipt.date}</p>}
          </div>
          <OcrBadge status={receipt.ocr_status} />
        </div>
        <div className="flex flex-wrap gap-4 text-sm text-gray-600">
          {receipt.total != null && (
            <span>Total: <strong>€{receipt.total.toFixed(2)}</strong></span>
          )}
          {payer && <span>Payer: <strong>{payer.name}</strong></span>}
          {receipt.settled && (
            <span className="bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full text-xs">settled</span>
          )}
        </div>
      </div>

      <h2 className="text-lg font-medium text-gray-700 mb-3">Line Items</h2>

      <div className="space-y-3 mb-4">
        {items?.map((item) => (
          <div key={item.id} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">
                {item.description ?? '(no description)'}
              </span>
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold text-gray-800">€{item.total.toFixed(2)}</span>
                <button
                  onClick={() => setExpandedItem(expandedItem === item.id ? null : item.id)}
                  className="text-xs text-blue-600 hover:underline"
                >
                  {expandedItem === item.id ? 'Close' : 'Allocate'}
                </button>
                <button
                  onClick={() => deleteMutation.mutate(item.id)}
                  className="text-xs text-red-400 hover:text-red-600"
                >
                  ✕
                </button>
              </div>
            </div>
            {expandedItem === item.id && (
              <div className="mt-3">
                <AllocationEditor
                  receiptId={receiptId}
                  itemId={item.id}
                  itemTotal={item.total}
                  participants={participants}
                />
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Add Item</h3>
        <div className="flex gap-2">
          <input
            value={addDesc}
            onChange={(e) => setAddDesc(e.target.value)}
            placeholder="Description"
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <input
            value={addTotal}
            onChange={(e) => setAddTotal(e.target.value)}
            placeholder="€0.00"
            type="number"
            step="0.01"
            className="w-24 border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <button
            onClick={() => addTotal && addMutation.mutate()}
            disabled={!addTotal || addMutation.isPending}
            className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            Add
          </button>
        </div>
      </div>
    </div>
  )
}
