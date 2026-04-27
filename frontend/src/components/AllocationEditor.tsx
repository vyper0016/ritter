import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getAllocations, setAllocations } from '../api/allocations'
import type { SplitType, User } from '../types'
import { pictureUrl } from '../api/users'

interface Props {
  receiptId: number
  itemId: number
  itemTotal: number
  participants: User[]
  compact?: boolean
}

interface Row {
  user_id: number
  enabled: boolean
  split_value: string
}

type QuickChoice = 'split' | `user:${number}`

export default function AllocationEditor({
  receiptId,
  itemId,
  itemTotal,
  participants,
  compact = false,
}: Props) {
  const qc = useQueryClient()
  const { data: existing } = useQuery({
    queryKey: ['allocations', receiptId, itemId],
    queryFn: () => getAllocations(receiptId, itemId),
  })

  const [rows, setRows] = useState<Row[]>([])
  const [splitType, setSplitType] = useState<SplitType>('equal')
  const [quickChoice, setQuickChoice] = useState<QuickChoice>('split')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const autoAppliedDefault = useRef(false)
  const [imageErrors, setImageErrors] = useState<Record<number, boolean>>({})

  const [validationError, setValidationError] = useState('')

  const quickMutation = useMutation({
    mutationFn: (choice: QuickChoice) => {
      const participantsPayload =
        choice === 'split'
          ? participants.map((u) => ({ user_id: u.id, value: null }))
          : [
              {
                user_id: Number(choice.replace('user:', '')),
                value: null,
              },
            ]

      return setAllocations(receiptId, itemId, {
        split_type: 'equal',
        participants: participantsPayload,
      })
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['allocations', receiptId, itemId] })
      qc.invalidateQueries({ queryKey: ['settle-preview'] })
    },
  })

  const mutation = useMutation({
    mutationFn: (payload: Row[]) => {
      const active = payload.filter((r) => r.enabled)
      return setAllocations(
        receiptId,
        itemId,
        {
          split_type: splitType,
          participants: active.map((r) => ({
            user_id: r.user_id,
            value: splitType === 'equal'
              ? null
              : r.split_value !== '' ? Number(r.split_value) : null,
          })),
        },
      )
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['allocations', receiptId, itemId] })
      qc.invalidateQueries({ queryKey: ['settle-preview'] })
    },
  })

  function setRow(i: number, patch: Partial<Row>) {
    setRows((prev) => prev.map((r, idx) => (idx === i ? { ...r, ...patch } : r)))
  }

  useEffect(() => {
    if (!participants.length) {
      setRows([])
      return
    }

    const nextRows = participants.map((u) => {
      const a = existing?.find((x) => x.user_id === u.id)
      return {
        user_id: u.id,
        enabled: !!a,
        split_value: a?.split_value != null ? String(a.split_value) : '',
      }
    })
    setRows(nextRows)
    const firstActive = existing?.find((x) => x.split_type)
    setSplitType((firstActive?.split_type ?? 'equal') as SplitType)

    if (!existing || existing.length === 0) {
      setQuickChoice('split')
      return
    }

    if (existing.length === 1) {
      setQuickChoice(`user:${existing[0].user_id}`)
    } else {
      setQuickChoice('split')
    }
  }, [existing, participants])

  useEffect(() => {
    if (autoAppliedDefault.current) return
    if (!participants.length) return
    if (!existing) return
    if (existing.length > 0) return

    autoAppliedDefault.current = true
    quickMutation.mutate('split')
  }, [existing, participants, quickMutation])

  function validate(): boolean {
    const active = rows.filter((r) => r.enabled)
    if (active.length === 0) {
      setValidationError('Select at least one participant')
      return false
    }
    if (splitType === 'percentage') {
      const sum = active.reduce((s, r) => s + (Number(r.split_value) || 0), 0)
      if (Math.abs(sum - 100) > 0.01) {
        setValidationError(`Percentages must sum to 100 (currently ${sum.toFixed(1)})`)
        return false
      }
    }
    if (splitType === 'fraction') {
      const sum = active.reduce((s, r) => s + (Number(r.split_value) || 0), 0)
      if (sum <= 0) {
        setValidationError('Fraction values must sum to a positive number')
        return false
      }
    }
    setValidationError('')
    return true
  }

  const activeCount = rows.filter((r) => r.enabled).length
  const quickValueSet = useMemo(
    () => new Set(['split', ...participants.map((u) => `user:${u.id}`)]),
    [participants],
  )
  const selectedQuick = quickValueSet.has(quickChoice) ? quickChoice : 'split'

  function initials(name: string): string {
    const parts = name.split(/\s+/).filter(Boolean)
    if (parts.length === 0) return '?'
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }

  const advancedPanel = (
    <>
      <div className="flex items-center gap-2">
        <label className="text-xs text-gray-500">Split:</label>
        <select
          value={splitType}
          onChange={(e) => {
            setSplitType(e.target.value as SplitType)
            setRows((prev) => prev.map((r) => ({ ...r, split_value: '' })))
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
        {mutation.isPending ? 'Saving...' : 'Save allocation'}
      </button>
    </>
  )

  return (
    <div className={compact ? 'relative' : 'border border-gray-200 rounded-lg p-3 space-y-3'}>
      <div className={compact ? 'flex items-center gap-1' : 'flex items-center gap-4 flex-wrap'}>
        <label className={compact ? 'hidden' : 'text-xs font-medium text-gray-600'}>Quick allocation:</label>
        <label
          title="Split evenly"
          className={compact ? 'flex items-center' : 'flex items-center gap-1 text-xs text-gray-700'}
        >
          <input
            type="radio"
            name={`quick-alloc-${itemId}`}
            checked={selectedQuick === 'split'}
            onChange={() => {
              setQuickChoice('split')
              quickMutation.mutate('split')
            }}
            className={compact ? 'sr-only' : ''}
          />
          <span
            className={
              compact
                ? `w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold cursor-pointer ${selectedQuick === 'split' ? 'bg-blue-500 text-white border-2 border-blue-500' : 'bg-gray-100 text-gray-500 border-2 border-gray-200 hover:border-gray-400'}`
                : 'text-xs text-gray-700'
            }
          >
            {compact ? '=' : 'Split'}
          </span>
        </label>

        {participants.map((u) => {
          const v = `user:${u.id}` as QuickChoice
          const selected = selectedQuick === v
          const useImage = !!u.profile_picture_filename && !imageErrors[u.id]
          return (
            <label key={u.id} title={u.name} className="flex items-center">
              <input
                type="radio"
                name={`quick-alloc-${itemId}`}
                checked={selected}
                onChange={() => {
                  setQuickChoice(v)
                  quickMutation.mutate(v)
                }}
                className="sr-only"
              />
              <span
                className={`w-8 h-8 rounded-full flex-shrink-0 cursor-pointer p-0.5 ${selected ? 'bg-blue-500' : 'bg-gray-300 hover:bg-gray-400'}`}
              >
                {useImage ? (
                  <span className="w-full h-full rounded-full overflow-hidden block relative">
                    <img
                      src={pictureUrl(u.id)}
                      alt={u.name}
                      className="w-full h-full object-cover"
                      onError={() => setImageErrors((prev) => ({ ...prev, [u.id]: true }))}
                    />
                    {selected && <span className="absolute inset-0 bg-blue-500/30" />}
                  </span>
                ) : (
                  <span className={`w-full h-full rounded-full flex items-center justify-center text-xs font-bold ${selected ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-500'}`}>
                    {initials(u.name)}
                  </span>
                )}
              </span>
            </label>
          )
        })}

        <button
          type="button"
          onClick={() => setShowAdvanced((v) => !v)}
          aria-label={showAdvanced ? 'Hide extra allocation options' : 'Show extra allocation options'}
          title={showAdvanced ? 'Hide extra options' : 'Extra options'}
          className={
            compact
              ? 'ml-1 w-8 h-8 rounded-full ring-2 ring-gray-200 hover:ring-gray-400 text-gray-500 hover:bg-gray-50 flex items-center justify-center text-sm leading-none'
              : 'text-xs text-blue-600 hover:underline'
          }
        >
          {compact ? '⚙' : showAdvanced ? 'Hide extra options' : 'Extra options'}
        </button>
      </div>

      {quickMutation.isPending && <p className="text-xs text-gray-500">Saving quick allocation...</p>}
      {quickMutation.isError && <p className="text-red-500 text-xs">Quick allocation failed</p>}

      {showAdvanced && (
        <div
          className={
            compact
              ? 'absolute right-0 top-8 z-20 w-72 border border-gray-200 rounded-lg bg-white p-3 space-y-3 shadow-lg'
              : 'space-y-3'
          }
        >
          {advancedPanel}
        </div>
      )}
    </div>
  )
}
