import { Link } from 'react-router-dom'
import OcrBadge from './OcrBadge'
import VendorLogo from './VendorLogo'
import type { Receipt } from '../types'

interface Props {
  receipt: Receipt
  selected?: boolean
  onToggleSelect?: (id: number) => void
}

export default function ReceiptCard({ receipt, selected = false, onToggleSelect }: Props) {
  return (
    <div className="relative">
      {onToggleSelect && (
        <div
          className="absolute left-3 top-1/2 -translate-y-1/2 z-10"
          onClick={(e) => {
            e.preventDefault()
            e.stopPropagation()
            onToggleSelect(receipt.id)
          }}
        >
          <input
            type="checkbox"
            checked={selected}
            onChange={() => {}}
            className="w-4 h-4 cursor-pointer accent-blue-600"
          />
        </div>
      )}
      <Link
        to={`/receipts/${receipt.id}`}
        className={`block bg-white rounded-xl border p-4 hover:shadow-sm transition-shadow ${
          onToggleSelect ? 'pl-10' : ''
        } ${selected ? 'border-blue-300 bg-blue-50' : 'border-gray-200'}`}
      >
        <div className="flex items-center justify-between mb-2">
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
    </div>
  )
}
