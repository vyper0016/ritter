import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getReceipt, getItems, addItem, deleteItem, deleteReceipt, updateReceiptMeta } from '../api/receipts'
import { getUsers } from '../api/users'
import OcrBadge from './OcrBadge'
import AllocationEditor from './AllocationEditor'
import { useAuth } from '../contexts/AuthContext'

const POLL_STATUSES = new Set(['pending', 'processing'])

interface Props {
  receiptId: number
  onDeleted?: () => void
}

export default function ReceiptPanel({ receiptId, onDeleted }: Props) {
  const navigate = useNavigate()
  const { user } = useAuth()
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
  const [vendorInput, setVendorInput] = useState('')
  const [dateInput, setDateInput] = useState('')

  const addMutation = useMutation({
    mutationFn: () =>
      addItem(receiptId, { description: addDesc || undefined, total: Number(addTotal) }),
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

  const deleteReceiptMutation = useMutation({
    mutationFn: () => deleteReceipt(receiptId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['receipts'] })
      if (onDeleted) onDeleted()
      else navigate('/')
    },
  })

  const updateMetaMutation = useMutation({
    mutationFn: () =>
      updateReceiptMeta(receiptId, {
        vendor_name: vendorInput.trim() || null,
        date: dateInput || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['receipt', receiptId] })
      qc.invalidateQueries({ queryKey: ['receipts'] })
    },
  })

  const participants = users?.filter((u) => receipt?.participant_ids.includes(u.id)) ?? []
  const payer = users?.find((u) => u.id === receipt?.payer_id)
  const canDeleteReceipt = user?.id === receipt?.created_by_id
  const canEditMeta = user?.id === receipt?.created_by_id

  useEffect(() => {
    if (!receipt) return
    setVendorInput(receipt.vendor_name ?? '')
    setDateInput(receipt.date ?? '')
  }, [receipt?.id, receipt?.vendor_name, receipt?.date])

  if (!receipt) return <div className="p-4 text-gray-400 text-sm">Loading…</div>

  return (
    <div>
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-800">
              {receipt.vendor_name ?? 'Receipt #' + receipt.id}
            </h2>
            {receipt.date && <p className="text-sm text-gray-500 mt-0.5">{receipt.date}</p>}
          </div>
          <div className="flex items-center gap-2">
            <OcrBadge status={receipt.ocr_status} />
            {canDeleteReceipt && (
              <button
                type="button"
                onClick={() => {
                  if (!window.confirm('Delete this receipt?')) return
                  deleteReceiptMutation.mutate()
                }}
                disabled={deleteReceiptMutation.isPending}
                className="text-xs border border-red-200 text-red-700 rounded-md px-2 py-1 hover:bg-red-50 disabled:opacity-50"
              >
                {deleteReceiptMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-4 text-sm text-gray-600">
          {receipt.total != null && (
            <span>
              Total: <strong>€{receipt.total.toFixed(2)}</strong>
            </span>
          )}
          {payer && (
            <span>
              Payer: <strong>{payer.name}</strong>
            </span>
          )}
          {receipt.settled && (
            <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded-full text-xs">
              settled
            </span>
          )}
        </div>
        {canEditMeta && (
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-[1fr_auto_auto] gap-2 items-end">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Vendor</label>
              <input
                value={vendorInput}
                onChange={(e) => setVendorInput(e.target.value)}
                placeholder="Vendor name"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Date</label>
              <input
                type="date"
                value={dateInput}
                onChange={(e) => setDateInput(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <button
              type="button"
              onClick={() => updateMetaMutation.mutate()}
              disabled={updateMetaMutation.isPending}
              className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {updateMetaMutation.isPending ? 'Saving...' : 'Save'}
            </button>
          </div>
        )}
      </div>

      <div className="space-y-3 mb-4">
        {items?.map((item) => (
          <div key={item.id} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center justify-between">
              <div className="min-w-0 flex-1">
                <span className="text-sm font-medium text-gray-700">
                  {item.description ?? '(no description)'}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold text-gray-800">
                  €{item.total.toFixed(2)}
                </span>
                <AllocationEditor
                  receiptId={receiptId}
                  itemId={item.id}
                  itemTotal={item.total}
                  participants={participants}
                  compact
                />
                <button
                  onClick={() => deleteMutation.mutate(item.id)}
                  className="text-xs text-red-400 hover:text-red-600"
                >
                  ✕
                </button>
              </div>
            </div>
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
