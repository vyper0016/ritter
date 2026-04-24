import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getUsers, updateUserName } from '../api/users'
import { createUser, deleteUser, setUserAdmin } from '../api/admin'
import { useAuth } from '../contexts/AuthContext'
import type { User } from '../types'

function UserRow({ u, currentUserId }: { u: User; currentUserId: number | undefined }) {
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [nameInput, setNameInput] = useState(u.name)

  const renameMutation = useMutation({
    mutationFn: (name: string) => updateUserName(u.id, name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      setEditing(false)
    },
  })

  const setAdminMutation = useMutation({
    mutationFn: (isAdmin: boolean) => setUserAdmin(u.id, isAdmin),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteUser(u.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })

  const isSelf = currentUserId === u.id
  const busy = renameMutation.isPending || setAdminMutation.isPending || deleteMutation.isPending

  return (
    <div className="bg-white rounded-xl border border-gray-200 px-4 py-3 flex items-center justify-between gap-3">
      <div className="min-w-0 flex-1">
        {editing ? (
          <div className="flex items-center gap-2">
            <input
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              autoFocus
              className="border border-gray-300 rounded-lg px-2 py-1 text-sm w-40"
              onKeyDown={(e) => {
                if (e.key === 'Enter') renameMutation.mutate(nameInput)
                if (e.key === 'Escape') { setEditing(false); setNameInput(u.name) }
              }}
            />
            <button
              onClick={() => renameMutation.mutate(nameInput)}
              disabled={renameMutation.isPending || !nameInput.trim()}
              className="text-xs bg-blue-600 text-white rounded px-2 py-1 hover:bg-blue-700 disabled:opacity-50"
            >
              {renameMutation.isPending ? '…' : 'Save'}
            </button>
            <button
              onClick={() => { setEditing(false); setNameInput(u.name) }}
              className="text-xs text-gray-400 hover:text-gray-600"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={() => setEditing(true)}
            className="text-left group"
          >
            <p className="text-sm font-medium text-gray-800 group-hover:text-blue-600">{u.name}</p>
            <p className="text-xs text-gray-400">@{u.username}</p>
          </button>
        )}
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        {u.is_admin && (
          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">admin</span>
        )}
        <button
          type="button"
          onClick={() => setAdminMutation.mutate(!u.is_admin)}
          disabled={busy || isSelf}
          className="text-xs border border-gray-300 rounded-md px-2 py-1 hover:bg-gray-50 disabled:opacity-50"
        >
          {u.is_admin ? 'Remove admin' : 'Make admin'}
        </button>
        <button
          type="button"
          onClick={() => {
            if (!window.confirm(`Delete user @${u.username}?`)) return
            deleteMutation.mutate()
          }}
          disabled={busy || isSelf}
          className="text-xs border border-red-200 text-red-700 rounded-md px-2 py-1 hover:bg-red-50 disabled:opacity-50"
        >
          Delete
        </button>
      </div>
    </div>
  )
}

export default function AdminPage() {
  const qc = useQueryClient()
  const { user: currentUser } = useAuth()
  const { data: users } = useQuery({ queryKey: ['users'], queryFn: getUsers })
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      setError('')
    },
    onError: () => setError('Failed to create user'),
  })

  async function handleAction(fd: FormData) {
    setError('')
    mutation.mutate({
      username: fd.get('username') as string,
      password: fd.get('password') as string,
      name: fd.get('name') as string,
      is_admin: fd.get('is_admin') === 'on',
    })
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-semibold text-gray-800 mb-6">Admin</h1>

      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-8">
        <h2 className="text-base font-medium text-gray-700 mb-4">Create User</h2>
        <form action={handleAction} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
              <input name="name" required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Username</label>
              <input name="username" required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Password</label>
              <input name="password" type="password" required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div className="flex items-center gap-2 pt-5">
              <input type="checkbox" name="is_admin" id="is_admin" />
              <label htmlFor="is_admin" className="text-sm text-gray-600">Admin</label>
            </div>
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          {mutation.isSuccess && <p className="text-green-600 text-sm">User created</p>}
          <button
            type="submit"
            disabled={mutation.isPending}
            className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {mutation.isPending ? 'Creating…' : 'Create user'}
          </button>
        </form>
      </div>

      <h2 className="text-base font-medium text-gray-700 mb-3">Users</h2>
      <div className="space-y-2">
        {users?.map((u) => (
          <UserRow key={u.id} u={u} currentUserId={currentUser?.id} />
        ))}
      </div>
    </div>
  )
}
