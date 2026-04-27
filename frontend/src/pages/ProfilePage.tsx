import { useRef, useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  uploadPicture,
  deletePicture,
  updateUserName,
  changePassword,
  listApiKeys,
  createApiKey,
  deleteApiKey,
} from '../api/users'
import type { CreatedApiKey } from '../api/users'
import { useAuth } from '../contexts/AuthContext'
import UserAvatar from '../components/UserAvatar'

export default function ProfilePage() {
  const { user, setUser } = useAuth()
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [nameInput, setNameInput] = useState('')

  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confirmPw, setConfirmPw] = useState('')
  const [pwError, setPwError] = useState('')
  const [pwSuccess, setPwSuccess] = useState(false)

  const [newKeyName, setNewKeyName] = useState('')
  const [createdKey, setCreatedKey] = useState<CreatedApiKey | null>(null)
  const [keyCopied, setKeyCopied] = useState(false)

  useEffect(() => {
    if (user) setNameInput(user.name)
  }, [user?.id])

  const nameMutation = useMutation({
    mutationFn: (name: string) => updateUserName(user!.id, name),
    onSuccess: (updated) => {
      setUser(updated)
      qc.invalidateQueries({ queryKey: ['users'] })
    },
  })

  const pictureMutation = useMutation({
    mutationFn: (file: File) => uploadPicture(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })

  const deletePictureMutation = useMutation({
    mutationFn: deletePicture,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })

  const passwordMutation = useMutation({
    mutationFn: () => changePassword(currentPw, newPw),
    onSuccess: () => {
      setCurrentPw('')
      setNewPw('')
      setConfirmPw('')
      setPwError('')
      setPwSuccess(true)
      setTimeout(() => setPwSuccess(false), 3000)
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : 'Failed to change password'
      setPwError(msg.includes('Current password') ? 'Current password incorrect' : 'Failed to change password')
    },
  })

  function submitPassword() {
    setPwError('')
    setPwSuccess(false)
    if (!currentPw || !newPw) {
      setPwError('Fill in all fields')
      return
    }
    if (newPw !== confirmPw) {
      setPwError('New passwords do not match')
      return
    }
    if (newPw.length < 6) {
      setPwError('New password must be at least 6 characters')
      return
    }
    passwordMutation.mutate()
  }

  const { data: apiKeys } = useQuery({ queryKey: ['api-keys'], queryFn: listApiKeys })

  const createKeyMutation = useMutation({
    mutationFn: (name: string) => createApiKey(name),
    onSuccess: (created) => {
      setCreatedKey(created)
      setNewKeyName('')
      setKeyCopied(false)
      qc.invalidateQueries({ queryKey: ['api-keys'] })
    },
  })

  const deleteKeyMutation = useMutation({
    mutationFn: (id: number) => deleteApiKey(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['api-keys'] }),
  })

  function copyKey() {
    if (!createdKey) return
    navigator.clipboard.writeText(createdKey.key)
    setKeyCopied(true)
    setTimeout(() => setKeyCopied(false), 2000)
  }

  if (!user) return null

  return (
    <div className="max-w-lg mx-auto py-8 px-4">
      <h1 className="text-2xl font-semibold text-gray-800 mb-6">Profile</h1>

      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
        <h2 className="text-sm font-medium text-gray-700 mb-4">Display Name</h2>
        <div className="flex gap-2">
          <input
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <button
            onClick={() => nameMutation.mutate(nameInput)}
            disabled={nameMutation.isPending || !nameInput.trim() || nameInput === user.name}
            className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {nameMutation.isPending ? 'Saving…' : 'Save'}
          </button>
        </div>
        {nameMutation.isError && (
          <p className="text-red-500 text-xs mt-1">Failed to update name</p>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
        <h2 className="text-sm font-medium text-gray-700 mb-4">Profile Picture</h2>
        <div className="flex items-center gap-4">
          <UserAvatar user={user} size={16} />
          <div className="flex flex-col gap-2">
            <button
              onClick={() => fileRef.current?.click()}
              className="text-sm text-blue-600 hover:underline"
            >
              {pictureMutation.isPending ? 'Uploading…' : 'Upload new picture'}
            </button>
            {user.profile_picture_filename && (
              <button
                onClick={() => deletePictureMutation.mutate()}
                className="text-sm text-red-400 hover:text-red-600"
              >
                {deletePictureMutation.isPending ? 'Removing…' : 'Remove picture'}
              </button>
            )}
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) pictureMutation.mutate(f)
            }}
          />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
        <h2 className="text-sm font-medium text-gray-700 mb-4">Change Password</h2>
        <div className="space-y-2">
          <input
            type="password"
            value={currentPw}
            onChange={(e) => setCurrentPw(e.target.value)}
            placeholder="Current password"
            autoComplete="current-password"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <input
            type="password"
            value={newPw}
            onChange={(e) => setNewPw(e.target.value)}
            placeholder="New password"
            autoComplete="new-password"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <input
            type="password"
            value={confirmPw}
            onChange={(e) => setConfirmPw(e.target.value)}
            placeholder="Confirm new password"
            autoComplete="new-password"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <button
            onClick={submitPassword}
            disabled={passwordMutation.isPending}
            className="w-full bg-blue-600 text-white rounded-lg py-2 text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {passwordMutation.isPending ? 'Updating…' : 'Update Password'}
          </button>
          {pwError && <p className="text-red-500 text-xs">{pwError}</p>}
          {pwSuccess && <p className="text-green-600 text-xs">Password updated</p>}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="text-sm font-medium text-gray-700 mb-1">API Keys</h2>
        <p className="text-xs text-gray-500 mb-4">
          Use API keys to upload receipts from automations like n8n. Send the key as the <code className="bg-gray-100 px-1 rounded">X-API-Key</code> header to <code className="bg-gray-100 px-1 rounded">POST /api/receipts</code>.
        </p>

        {createdKey && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
            <p className="text-xs text-yellow-800 font-medium mb-2">
              Copy your new key — it will not be shown again.
            </p>
            <div className="flex gap-2 items-center">
              <code className="flex-1 bg-white border border-yellow-200 rounded px-2 py-1 text-xs break-all">
                {createdKey.key}
              </code>
              <button
                onClick={copyKey}
                className="text-xs bg-yellow-600 text-white rounded px-3 py-1 hover:bg-yellow-700"
              >
                {keyCopied ? 'Copied' : 'Copy'}
              </button>
            </div>
            <button
              onClick={() => setCreatedKey(null)}
              className="text-xs text-yellow-700 hover:underline mt-2"
            >
              Done
            </button>
          </div>
        )}

        <div className="flex gap-2 mb-4">
          <input
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder="Key name (e.g. n8n upload)"
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <button
            onClick={() => createKeyMutation.mutate(newKeyName.trim())}
            disabled={createKeyMutation.isPending || !newKeyName.trim()}
            className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {createKeyMutation.isPending ? 'Creating…' : 'Create'}
          </button>
        </div>

        {apiKeys && apiKeys.length > 0 ? (
          <ul className="divide-y divide-gray-100">
            {apiKeys.map((k) => (
              <li key={k.id} className="py-2 flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-800 truncate">{k.name}</div>
                  <div className="text-xs text-gray-400">
                    <code>{k.key_prefix}…</code> · created {new Date(k.created_at).toLocaleDateString()}
                    {k.last_used_at && ` · last used ${new Date(k.last_used_at).toLocaleDateString()}`}
                  </div>
                </div>
                <button
                  onClick={() => {
                    if (confirm(`Delete key "${k.name}"?`)) deleteKeyMutation.mutate(k.id)
                  }}
                  className="text-xs text-red-400 hover:text-red-600"
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-gray-400">No API keys yet.</p>
        )}
      </div>
    </div>
  )
}
