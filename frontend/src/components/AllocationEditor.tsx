import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getAllocations, setAllocations } from '../api/allocations'
import type { SplitType, User } from '../types'

interface Props {
  receiptId: number
  itemId: number
  itemTotal: number
  participants: User[]
}

interface Row {
  user_id: number
  enabled: boolean
  split_type: SplitType
  split_value: string
}

export default function AllocationEditor({ receiptId, itemId, itemTotal, participants }: Props) {
  const qc = useQueryClient()
  const { data: existing } = useQuery({
    queryKey: ['allocations', receiptId, itemId],
    queryFn: () => getAllocations(receiptId, itemId),
  })

  const [rows, setRows] = useState<Row[]>(() => {
    return participants.map((u) => {
      const a = existing?.find((x) => x.user_id === u.id)
      return {
        user_id: u.id,
        enabled: !!a,
        split_type: (a?.split_type ?? 'equal') as SplitType,
        split_value: a?.split_value != null ? String(a.split_value) : '',
      }
    })
  })

  const [validationError, setValidationError] = useState('')

  const mutation = useMutation({
    mutationFn: (payload: Row[]) => {
      const active = payload.filter((r) => r.enabled)
      return setAllocations(
        receiptId,
        itemId,
        active.map((r) => ({
          user_id: r.user_id,
          split_type: r.split_type,
          split_value: r.split_value !== '' ? Number(r.split_value) : null,
        })),
      )
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['allocations', receiptId, itemId] })
    },
  })

  function setRow(i: number, patch: Partial<Row>) {
    setRows((prev) => prev.map((r, idx) => (idx === i ? { ...r, ...patch } : r)))
  }

  function validate(): boolean {
    const active = rows.filter((r) => r.enabled)
    if (active.length === 0) {
      setValidationError('Select at least one participant')
      return false
    }
    if (active[0].split_type === 'percentage') {
      const sum = active.reduce((s, r) => s + (Number(r.split_value) || 0), 0)
      if (Math.abs(sum - 100) > 0.01) {
        setValidationError(`Percentages must sum to 100 (currently ${sum.toFixed(1)})`)
        return false
      }
    }
    setValidationError('')
    return true
  }

  const splitType = rows[0]?.split_type ?? 'equal'
  const activeCount = rows.filter((r) => r.enabled).length

  return (
    <div className="border border-gray-200 rounded-lg p-3 space-y-3">
      <div className="flex items-center gap-2">
        <label className="text-xs text-gray-500">Split:</label>
        <select
          value={splitType}
          onChange={(e) => {
            const t = e.target.value as SplitType
            setRows((prev) => prev.map((r) => ({ ...r, split_type: t, split_value: '' })))
          }}
          className="text-xs border border-gray-300 rounded px-2 py-1"
        >
          <option value="equal">Equal</option>
          <option value="percentage">Percentage</option>
          <option value="fraction">Fraction</option>
        </select>
      </div>

      <div className="space-y-2">
        {rows.map((row, i) => {
          const u = participants.find((p) => p.id === row.user_id)!
          return (
            <div key={row.user_id} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={row.enabled}
                onChange={(e) => setRow(i, { enabled: e.target.checked })}
              />
              <span className="text-sm flex-1">{u.name}</span>
              {splitType !== 'equal' && row.enabled && (
                <input
                  type="number"
                  step="any"
                  value={row.split_value}
                  onChange={(e) => setRow(i, { split_value: e.target.value })}
                  placeholder={splitType === 'percentage' ? '%' : 'n'}
                  className="w-20 border border-gray-300 rounded px-2 py-0.5 text-xs"
                />
              )}
              {splitType === 'equal' && row.enabled && activeCount > 0 && (
                <span className="text-xs text-gray-400">
                  €{(itemTotal / activeCount).toFixed(2)}
                </span>
              )}
            </div>
          )
        })}
      </div>

      {validationError && <p className="text-red-500 text-xs">{validationError}</p>}
      {mutation.isSuccess && <p className="text-green-600 text-xs">Saved</p>}
      {mutation.isError && <p className="text-red-500 text-xs">Save failed</p>}

      <button
        onClick={() => validate() && mutation.mutate(rows)}
        disabled={mutation.isPending}
        className="text-xs bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {mutation.isPending ? 'Saving…' : 'Save allocation'}
      </button>
    </div>
  )
}
