import { Link } from 'react-router-dom'
import OcrBadge from './OcrBadge'
import type { Receipt } from '../types'

export default function ReceiptCard({ receipt }: { receipt: Receipt }) {
  return (
    <Link
      to={`/receipts/${receipt.id}`}
      className="block bg-white rounded-xl border border-gray-200 p-4 hover:shadow-sm transition-shadow"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-gray-800 truncate">
          {receipt.vendor_name ?? 'Unknown vendor'}
        </span>
        <OcrBadge status={receipt.ocr_status} />
      </div>
      <div className="flex items-center justify-between text-sm text-gray-500">
        <span>{receipt.date ?? '—'}</span>
        <div className="flex items-center gap-2">
          {receipt.total != null && (
            <span className="font-medium text-gray-700">€{receipt.total.toFixed(2)}</span>
          )}
          {receipt.settled && (
            <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
              settled
            </span>
          )}
        </div>
      </div>
    </Link>
  )
}
