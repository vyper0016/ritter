import { useRef, useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { uploadPicture, deletePicture, updateUserName } from '../api/users'
import { useAuth } from '../contexts/AuthContext'
import UserAvatar from '../components/UserAvatar'

export default function ProfilePage() {
  const { user, setUser } = useAuth()
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [nameInput, setNameInput] = useState('')

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

      <div className="bg-white rounded-xl border border-gray-200 p-5">
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
    </div>
  )
}
