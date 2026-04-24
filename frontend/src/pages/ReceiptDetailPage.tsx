import { useParams } from 'react-router-dom'
import ReceiptPanel from '../components/ReceiptPanel'

export default function ReceiptDetailPage() {
  const { id } = useParams<{ id: string }>()
  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <ReceiptPanel receiptId={Number(id)} />
    </div>
  )
}
