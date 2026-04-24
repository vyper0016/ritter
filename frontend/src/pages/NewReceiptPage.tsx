import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { createReceipt } from '../api/receipts'
import { getUsers, getDefaults } from '../api/users'
import { useAuth } from '../contexts/AuthContext'

export default function NewReceiptPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [payerId, setPayerId] = useState<number>(0)
  const [participants, setParticipants] = useState<number[]>([])
  const [image, setImage] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const { data: users } = useQuery({ queryKey: ['users'], queryFn: getUsers })
  const { data: defaults } = useQuery({ queryKey: ['defaults'], queryFn: getDefaults })

  useEffect(() => {
    if (user && payerId === 0) setPayerId(user.id)
  }, [user, payerId])

  useEffect(() => {
    if (defaults && participants.length === 0) setParticipants(defaults)
  }, [defaults, participants.length])

  function toggleParticipant(id: number) {
    setParticipants((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    )
  }

  async function submit() {
    if (!payerId || participants.length === 0) {
      setError('Select payer and at least one participant')
      return
    }
    setLoading(true)
    setError('')
    try {
      const r = await createReceipt({ payer_id: payerId, participant_ids: participants, image: image ?? undefined })
      navigate(`/receipts/${r.id}`)
    } catch {
      setError('Failed to create receipt')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-lg mx-auto py-8 px-4">
      <h1 className="text-2xl font-semibold text-gray-800 mb-6">New Receipt</h1>

      <div className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Image (optional)</label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setImage(e.target.files?.[0] ?? null)}
            className="text-sm text-gray-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Payer</label>
          <select
            value={payerId}
            onChange={(e) => setPayerId(Number(e.target.value))}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            {users?.map((u) => (
              <option key={u.id} value={u.id}>{u.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Participants</label>
          <div className="space-y-2">
            {users?.map((u) => (
              <label key={u.id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={participants.includes(u.id)}
                  onChange={() => toggleParticipant(u.id)}
                  className="rounded"
                />
                {u.name}
              </label>
            ))}
          </div>
        </div>

        {error && <p className="text-red-500 text-sm">{error}</p>}

        <div className="flex gap-3">
          <button
            onClick={() => navigate('/')}
            className="flex-1 border border-gray-300 text-gray-700 rounded-lg py-2 text-sm hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={loading}
            className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Creating…' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  )
}
