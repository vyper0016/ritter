import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listReceipts, createReceipt, deleteReceipt } from '../api/receipts'
import { getUsers } from '../api/users'
import { useAuth } from '../contexts/AuthContext'
import ReceiptCard from '../components/ReceiptCard'
import type { ListReceiptsParams } from '../api/receipts'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const qc = useQueryClient()
  const quickUploadRef = useRef<HTMLInputElement>(null)
  const [settled, setSettled] = useState<boolean | undefined>(undefined)
  const [role, setRole] = useState<ListReceiptsParams['role']>(undefined)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [sortBy, setSortBy] = useState<'date' | 'vendor'>('date')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const { data: receipts, isLoading } = useQuery({
    queryKey: ['receipts', settled, role],
    queryFn: () => listReceipts({ settled, role }),
  })

  const { data: users } = useQuery({ queryKey: ['users'], queryFn: getUsers })

  const deleteSelectedMutation = useMutation({
    mutationFn: async (ids: number[]) => {
      await Promise.all(ids.map((id) => deleteReceipt(id)))
    },
    onSuccess: () => {
      setSelectedIds(new Set())
      qc.invalidateQueries({ queryKey: ['receipts'] })
      qc.invalidateQueries({ queryKey: ['settle-preview'] })
    },
  })

  const quickUploadMutation = useMutation({
    mutationFn: (image: File) =>
      createReceipt({
        payer_id: user!.id,
        participant_ids: users?.map((u) => u.id) ?? [user!.id],
        image,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['receipts'] })
    },
  })

  function toggleSelect(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const unsettledVisible = receipts?.filter((r) => !r.settled) ?? []
  const showSettleUI = true

  function toggleSort(field: 'date' | 'vendor') {
    if (sortBy === field) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortBy(field); setSortDir(field === 'date' ? 'desc' : 'asc') }
  }

  const sortedReceipts = receipts ? [...receipts].sort((a, b) => {
    let cmp = 0
    if (sortBy === 'date') {
      const da = a.date ?? ''
      const db = b.date ?? ''
      cmp = da < db ? -1 : da > db ? 1 : 0
    } else {
      const va = (a.vendor_name ?? '').toLowerCase()
      const vb = (b.vendor_name ?? '').toLowerCase()
      cmp = va < vb ? -1 : va > vb ? 1 : 0
    }
    return sortDir === 'asc' ? cmp : -cmp
  }) : undefined

  function goSettle(ids: number[]) {
    if (ids.length === 0) return
    navigate('/settle', { state: { receiptIds: ids } })
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-800">Receipts</h1>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          {selectedIds.size > 0 && (
            <button
              onClick={() => {
                if (!window.confirm(`Delete ${selectedIds.size} receipt(s)?`)) return
                deleteSelectedMutation.mutate([...selectedIds])
              }}
              disabled={deleteSelectedMutation.isPending}
              className="border border-red-300 text-red-600 text-sm px-4 py-2 rounded-lg hover:bg-red-50 disabled:opacity-50"
            >
              {deleteSelectedMutation.isPending ? 'Deleting…' : `Delete (${selectedIds.size})`}
            </button>
          )}
          {showSettleUI && selectedIds.size > 0 && [...selectedIds].some((id) => receipts?.find((r) => r.id === id && !r.settled)) && (
            <button
              onClick={() => goSettle([...selectedIds].filter((id) => receipts?.find((r) => r.id === id && !r.settled)))}
              className="bg-green-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-green-700"
            >
              Settle selected ({[...selectedIds].filter((id) => receipts?.find((r) => r.id === id && !r.settled)).length})
            </button>
          )}
          {showSettleUI && unsettledVisible.length > 0 && (
            <button
              onClick={() => goSettle(unsettledVisible.map((r) => r.id))}
              className="border border-green-600 text-green-700 text-sm px-4 py-2 rounded-lg hover:bg-green-50"
            >
              Settle all
            </button>
          )}
          <button
            onClick={() => quickUploadRef.current?.click()}
            disabled={quickUploadMutation.isPending || !user}
            className="border border-gray-300 text-gray-700 text-sm px-4 py-2 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            {quickUploadMutation.isPending ? 'Uploading…' : '📷'}
          </button>
          <input
            ref={quickUploadRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) quickUploadMutation.mutate(f)
              e.target.value = ''
            }}
          />
          <Link
            to="/receipts/new"
            className="bg-blue-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            + New
          </Link>
        </div>
      </div>

      <div className="flex gap-2 mb-4 flex-wrap">
        <select
          value={settled === undefined ? 'all' : String(settled)}
          onChange={(e) => {
            const v = e.target.value
            setSettled(v === 'all' ? undefined : v === 'true')
            setSelectedIds(new Set())
          }}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
        >
          <option value="false">Unsettled</option>
          <option value="true">Settled</option>
          <option value="all">All</option>
        </select>

        <select
          value={role ?? 'all'}
          onChange={(e) => {
            const v = e.target.value as ListReceiptsParams['role'] | 'all'
            setRole(v === 'all' ? undefined : v)
          }}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
        >
          <option value="all">All roles</option>
          <option value="uploaded">Uploaded by me</option>
          <option value="participant">Participant</option>
        </select>

        <div className="flex items-center gap-1 ml-auto">
          <span className="text-xs text-gray-400">Sort:</span>
          {(['date', 'vendor'] as const).map((field) => (
            <button
              key={field}
              onClick={() => toggleSort(field)}
              className={`text-xs px-2.5 py-1.5 rounded-lg border ${sortBy === field ? 'border-blue-500 bg-blue-50 text-blue-700 font-medium' : 'border-gray-300 text-gray-600 hover:bg-gray-50'}`}
            >
              {field === 'date' ? 'Date' : 'Vendor'}{sortBy === field ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <p className="text-gray-400 text-sm">Loading…</p>}
      {receipts && receipts.length === 0 && (
        <p className="text-gray-400 text-sm">No receipts found.</p>
      )}
      <div className="space-y-3">
        {sortedReceipts?.map((r) => (
          <ReceiptCard
            key={r.id}
            receipt={r}
            selected={selectedIds.has(r.id)}
            onToggleSelect={toggleSelect}
          />
        ))}
      </div>
    </div>
  )
}
