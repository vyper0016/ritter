import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getUsers } from '../api/users'
import { createUser, deleteUser, setUserAdmin } from '../api/admin'
import { useAuth } from '../contexts/AuthContext'

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

  const setAdminMutation = useMutation({
    mutationFn: ({ userId, isAdmin }: { userId: number; isAdmin: boolean }) =>
      setUserAdmin(userId, isAdmin),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      setError('')
    },
    onError: () => setError('Failed to update admin status'),
  })

  const deleteMutation = useMutation({
    mutationFn: (userId: number) => deleteUser(userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      setError('')
    },
    onError: () => setError('Failed to delete user'),
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

  function handleSetAdmin(userId: number, isAdmin: boolean) {
    setError('')
    setAdminMutation.mutate({ userId, isAdmin })
  }

  function handleDeleteUser(userId: number, username: string) {
    if (!window.confirm(`Delete user @${username}?`)) return
    setError('')
    deleteMutation.mutate(userId)
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
          <div key={u.id} className="bg-white rounded-xl border border-gray-200 px-4 py-3 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-800">{u.name}</p>
              <p className="text-xs text-gray-400">@{u.username}</p>
            </div>
            <div className="flex items-center gap-2">
              {u.is_admin && (
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">admin</span>
              )}
              <button
                type="button"
                onClick={() => handleSetAdmin(u.id, !u.is_admin)}
                disabled={setAdminMutation.isPending || deleteMutation.isPending || currentUser?.id === u.id}
                className="text-xs border border-gray-300 rounded-md px-2 py-1 hover:bg-gray-50 disabled:opacity-50"
              >
                {u.is_admin ? 'Remove admin' : 'Make admin'}
              </button>
              <button
                type="button"
                onClick={() => handleDeleteUser(u.id, u.username)}
                disabled={deleteMutation.isPending || setAdminMutation.isPending || currentUser?.id === u.id}
                className="text-xs border border-red-200 text-red-700 rounded-md px-2 py-1 hover:bg-red-50 disabled:opacity-50"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
