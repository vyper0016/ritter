import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listReceipts } from '../api/receipts'
import ReceiptCard from '../components/ReceiptCard'
import type { ListReceiptsParams } from '../api/receipts'

export default function DashboardPage() {
  const [settled, setSettled] = useState<boolean | undefined>(false)
  const [role, setRole] = useState<ListReceiptsParams['role']>(undefined)

  const { data: receipts, isLoading } = useQuery({
    queryKey: ['receipts', settled, role],
    queryFn: () => listReceipts({ settled, role }),
  })

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-800">Receipts</h1>
        <Link
          to="/receipts/new"
          className="bg-blue-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          + New
        </Link>
      </div>

      <div className="flex gap-2 mb-4 flex-wrap">
        <select
          value={settled === undefined ? 'all' : String(settled)}
          onChange={(e) => {
            const v = e.target.value
            setSettled(v === 'all' ? undefined : v === 'true')
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
      </div>

      {isLoading && <p className="text-gray-400 text-sm">Loading…</p>}
      {receipts && receipts.length === 0 && (
        <p className="text-gray-400 text-sm">No receipts found.</p>
      )}
      <div className="space-y-3">
        {receipts?.map((r) => <ReceiptCard key={r.id} receipt={r} />)}
      </div>
    </div>
  )
}
