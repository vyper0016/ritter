import { useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getReceipt, getItems, addItem, deleteItem, updateReceiptMeta, updateItem, updateParticipants } from '../api/receipts'
import { getUsers } from '../api/users'
import OcrBadge from './OcrBadge'
import ReceiptImageZoom from './ReceiptImageZoom'
import AllocationEditor from './AllocationEditor'
import { useAuth } from '../contexts/AuthContext'

const POLL_STATUSES = new Set(['pending', 'processing'])

interface Props {
  receiptId: number
  onDeleted?: () => void
}

export default function ReceiptPanel({ receiptId }: Props) {
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

  const [payerPickerOpen, setPayerPickerOpen] = useState(false)
  const payerPickerRef = useRef<HTMLSpanElement>(null)
  useEffect(() => {
    if (!payerPickerOpen) return
    const handler = (e: MouseEvent) => {
      if (payerPickerRef.current && !payerPickerRef.current.contains(e.target as Node)) {
        setPayerPickerOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [payerPickerOpen])
  const [addDesc, setAddDesc] = useState('')
  const [addTotal, setAddTotal] = useState('')
  const [vendorInput, setVendorInput] = useState('')
  const [dateInput, setDateInput] = useState('')
  const [itemEdits, setItemEdits] = useState<Record<number, { description: string; total: string }>>({})
  const saveTimers = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map())
  const itemsRef = useRef(items)
  useEffect(() => { itemsRef.current = items }, [items])
  useEffect(() => () => saveTimers.current.forEach(clearTimeout), [])

  // Fetch receipt image as blob URL
  const imageObjRef = useRef<string | null>(null)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [imageMime, setImageMime] = useState<string | null>(null)
  useEffect(() => {
    if (!receipt?.image_filename) return
    const token = localStorage.getItem('token')
    let cancelled = false
    fetch(`/api/receipts/${receiptId}/image`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(async (resp) => {
        if (cancelled || !resp.ok) return
        const blob = await resp.blob()
        if (cancelled) return
        if (imageObjRef.current) URL.revokeObjectURL(imageObjRef.current)
        const url = URL.createObjectURL(blob)
        imageObjRef.current = url
        setImageUrl(url)
        setImageMime(blob.type || receipt.image_mimetype || null)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [receiptId, receipt?.image_filename])

  const addMutation = useMutation({
    mutationFn: () =>
      addItem(receiptId, { description: addDesc || undefined, total: Number(addTotal) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['items', receiptId] })
      qc.invalidateQueries({ queryKey: ['settle-preview'] })
      setAddDesc('')
      setAddTotal('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (itemId: number) => deleteItem(receiptId, itemId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['items', receiptId] })
      qc.invalidateQueries({ queryKey: ['settle-preview'] })
    },
  })

  const updateItemMutation = useMutation({
    mutationFn: ({ itemId, description, total }: { itemId: number; description?: string; total?: number }) =>
      updateItem(receiptId, itemId, { description, total }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['items', receiptId] })
      qc.invalidateQueries({ queryKey: ['receipt', receiptId] })
      qc.invalidateQueries({ queryKey: ['receipts'] })
      qc.invalidateQueries({ queryKey: ['settle-preview'] })
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

  const updatePayerMutation = useMutation({
    mutationFn: (newPayerId: number) =>
      updateParticipants(receiptId, {
        payer_id: newPayerId,
        participant_ids: receipt?.participant_ids ?? [],
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['receipt', receiptId] })
      qc.invalidateQueries({ queryKey: ['receipts'] })
      qc.invalidateQueries({ queryKey: ['settle-preview'] })
      setPayerPickerOpen(false)
    },
  })

  const participants = users?.filter((u) => receipt?.participant_ids.includes(u.id)) ?? []
  const payer = users?.find((u) => u.id === receipt?.payer_id)
  const canEditMeta = user?.id === receipt?.created_by_id

  // Initialize item edits when items load or change
  useEffect(() => {
    if (!items) return
    setItemEdits((prev) => {
      const next = { ...prev }
      for (const item of items) {
        if (!(item.id in next)) {
          next[item.id] = { description: item.description ?? '', total: item.total.toFixed(2) }
        }
      }
      return next
    })
  }, [items])

  function saveItemField(itemId: number, field: 'description' | 'total') {
    const edit = itemEdits[itemId]
    const item = items?.find((i) => i.id === itemId)
    if (!edit || !item) return
    if (field === 'description' && edit.description !== (item.description ?? '')) {
      updateItemMutation.mutate({ itemId, description: edit.description || undefined })
    } else if (field === 'total') {
      const newTotal = parseFloat(edit.total)
      if (!isNaN(newTotal) && Math.abs(newTotal - item.total) > 0.001) {
        updateItemMutation.mutate({ itemId, total: newTotal })
      }
    }
  }

  const itemsSum = items?.reduce((s, i) => s + i.total, 0) ?? 0
  const totalDiffers = receipt?.total != null && items != null && Math.abs(receipt.total - itemsSum) > 0.005

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
          </div>
        </div>
        <div className="flex flex-wrap gap-4 text-sm text-gray-600">
          {receipt.total != null && (
            <span>
              Total: <strong>€{receipt.total.toFixed(2)}</strong>
            </span>
          )}
          {payer && (
            <span className="relative" ref={payerPickerRef}>
              Payer:{' '}
              <button
                onClick={() => setPayerPickerOpen((o) => !o)}
                className="font-bold underline decoration-dotted cursor-pointer hover:text-blue-600"
              >
                {payer.name}
              </button>
              {payerPickerOpen && users && (
                <div className="absolute z-10 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-3 min-w-[160px]">
                  <p className="text-xs text-gray-500 mb-2 font-medium">Change payer</p>
                  <div className="space-y-1">
                    {users.map((u) => (
                      <label key={u.id} className="flex items-center gap-2 cursor-pointer text-sm py-0.5">
                        <input
                          type="radio"
                          name={`payer-${receiptId}`}
                          value={u.id}
                          checked={u.id === receipt.payer_id}
                          onChange={() => updatePayerMutation.mutate(u.id)}
                          disabled={updatePayerMutation.isPending}
                        />
                        {u.name}
                      </label>
                    ))}
                  </div>
                  <button
                    onClick={() => setPayerPickerOpen(false)}
                    className="mt-2 text-xs text-gray-400 hover:text-gray-600"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </span>
          )}
          <span>
            Uploaded: <strong>{new Date(receipt.created_at).toLocaleDateString()}</strong>
            {receipt.uploaded_through && (
              <span className="ml-1.5 text-xs text-gray-400">via {receipt.uploaded_through}</span>
            )}
          </span>
          {receipt.settled && receipt.settled_at && (
            <span>
              Settled: <strong>{new Date(receipt.settled_at).toLocaleDateString()}</strong>
            </span>
          )}
          {receipt.settled && (
            <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded-full text-xs">
              settled
            </span>
          )}
        </div>
        {totalDiffers && (
          <p className="mt-2 text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded px-2 py-1">
            ⚠ Receipt total €{receipt.total!.toFixed(2)} differs from items sum €{itemsSum.toFixed(2)}
          </p>
        )}
        {imageUrl && (
          <div className="mt-4">
            {imageMime === 'application/pdf' ? (
              <a
                href={imageUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 hover:bg-gray-50"
              >
                📄 {receipt.image_filename ?? 'Receipt PDF'}
              </a>
            ) : (
              <ReceiptImageZoom src={imageUrl} onClick={() => window.open(imageUrl, '_blank')} />
            )}
          </div>
        )}
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
        {items?.map((item) => {
          const edit = itemEdits[item.id] ?? { description: item.description ?? '', total: item.total.toFixed(2) }
          return (
            <div key={item.id} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-center gap-2">
                <input
                  className="flex-1 min-w-0 text-sm border border-gray-200 rounded px-2 py-1 focus:outline-none focus:border-blue-400"
                  value={edit.description}
                  placeholder="(no description)"
                  onChange={(e) =>
                    setItemEdits((prev) => ({
                      ...prev,
                      [item.id]: { ...edit, description: e.target.value },
                    }))
                  }
                  onBlur={() => saveItemField(item.id, 'description')}
                  onKeyDown={(e) => e.key === 'Enter' && saveItemField(item.id, 'description')}
                />
                <div className="flex items-center gap-1">
                  <span className="text-sm text-gray-500">€</span>
                  <input
                    className="w-20 text-sm font-semibold border border-gray-200 rounded px-2 py-1 focus:outline-none focus:border-blue-400 text-right"
                    type="number"
                    step="0.5"
                    value={edit.total}
                    onChange={(e) => {
                      const val = e.target.value
                      setItemEdits((prev) => ({
                        ...prev,
                        [item.id]: { ...edit, total: val },
                      }))
                      clearTimeout(saveTimers.current.get(item.id))
                      saveTimers.current.set(item.id, setTimeout(() => {
                        saveTimers.current.delete(item.id)
                        const newTotal = parseFloat(val)
                        const cur = itemsRef.current?.find((i) => i.id === item.id)
                        if (cur && !isNaN(newTotal) && Math.abs(newTotal - cur.total) > 0.001) {
                          updateItemMutation.mutate({ itemId: item.id, total: newTotal })
                        }
                      }, 600))
                    }}
                    onBlur={() => {
                      clearTimeout(saveTimers.current.get(item.id))
                      saveTimers.current.delete(item.id)
                      saveItemField(item.id, 'total')
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        clearTimeout(saveTimers.current.get(item.id))
                        saveTimers.current.delete(item.id)
                        saveItemField(item.id, 'total')
                      }
                    }}
                  />
                </div>
                <AllocationEditor
                  receiptId={receiptId}
                  itemId={item.id}
                  itemTotal={item.total}
                  participants={participants}
                  compact
                />
                <button
                  onClick={() => deleteMutation.mutate(item.id)}
                  className="text-xs text-red-400 hover:text-red-600 flex-shrink-0"
                >
                  ✕
                </button>
              </div>
            </div>
          )
        })}
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

