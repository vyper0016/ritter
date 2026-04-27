import { Link } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { deleteReceipt } from '../api/receipts'
import OcrBadge from './OcrBadge'
import VendorLogo from './VendorLogo'
import type { Receipt } from '../types'

interface Props {
  receipt: Receipt
  selected?: boolean
  onToggleSelect?: (id: number) => void
}

export default function ReceiptCard({ receipt, selected = false, onToggleSelect }: Props) {
  const qc = useQueryClient()
  const deleteMutation = useMutation({
    mutationFn: () => deleteReceipt(receipt.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['receipts'] })
      qc.invalidateQueries({ queryKey: ['settle-preview'] })
    },
  })

  function handleDelete(e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()
    if (!window.confirm('Delete this receipt?')) return
    deleteMutation.mutate()
  }

  return (
    <div
      className={`bg-white rounded-xl border flex items-center gap-3 px-3 py-3 ${
        selected ? 'border-blue-300 bg-blue-50' : 'border-gray-200'
      }`}
    >
      {onToggleSelect && (
        <input
          type="checkbox"
          checked={selected}
          onChange={() => onToggleSelect(receipt.id)}
          onClick={(e) => e.stopPropagation()}
          className="w-5 h-5 cursor-pointer accent-blue-600 flex-shrink-0"
        />
      )}
      <Link
        to="/settle"
        state={{ receiptIds: [receipt.id] }}
        className="flex-1 min-w-0 hover:opacity-80"
      >
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2 min-w-0">
            <VendorLogo vendorName={receipt.vendor_name} vendorLogoUrl={receipt.vendor_logo_url} />
            <span className="font-medium text-gray-800 truncate">
              {receipt.vendor_name ?? 'Unknown vendor'}
            </span>
          </div>
          <OcrBadge status={receipt.ocr_status} />
        </div>
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>{receipt.date ?? '—'}</span>
          <div className="flex items-center gap-2">
            {receipt.total != null && (
              <span className="font-medium text-gray-700">€{receipt.total.toFixed(2)}</span>
            )}
            {receipt.settled ? (
              <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                settled
              </span>
            ) : (
              <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                unsettled
              </span>
            )}
          </div>
        </div>
      </Link>
      <button
        onClick={handleDelete}
        disabled={deleteMutation.isPending}
        className="text-gray-300 hover:text-red-600 disabled:opacity-50 flex-shrink-0 px-2 py-1 text-base"
        title="Delete receipt"
      >
        ✕
      </button>
    </div>
  )
}
