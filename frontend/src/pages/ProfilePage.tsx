import { useRef, useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getUsers, getDefaults, setDefaults, uploadPicture, deletePicture } from '../api/users'
import { useAuth } from '../contexts/AuthContext'
import UserAvatar from '../components/UserAvatar'

export default function ProfilePage() {
  const { user } = useAuth()
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [saveMsg, setSaveMsg] = useState('')

  const { data: users } = useQuery({ queryKey: ['users'], queryFn: getUsers })
  const { data: defaults } = useQuery({ queryKey: ['defaults'], queryFn: getDefaults })
  const [selected, setSelected] = useState<number[]>([])

  useEffect(() => {
    if (defaults && defaults.length > 0) setSelected(defaults)
  }, [defaults])

  const defaultsMutation = useMutation({
    mutationFn: (ids: number[]) => setDefaults(ids),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['defaults'] })
      setSaveMsg('Saved')
      setTimeout(() => setSaveMsg(''), 2000)
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

  function toggleParticipant(id: number) {
    setSelected((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id])
  }

  if (!user) return null

  return (
    <div className="max-w-lg mx-auto py-8 px-4">
      <h1 className="text-2xl font-semibold text-gray-800 mb-6">Profile</h1>

      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
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

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="text-sm font-medium text-gray-700 mb-4">Default Participants</h2>
        <div className="space-y-2 mb-4">
          {users?.map((u) => (
            <label key={u.id} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={selected.includes(u.id)}
                onChange={() => toggleParticipant(u.id)}
              />
              {u.name}
            </label>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => defaultsMutation.mutate(selected)}
            disabled={defaultsMutation.isPending}
            className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            Save defaults
          </button>
          {saveMsg && <span className="text-green-600 text-sm">{saveMsg}</span>}
        </div>
      </div>
    </div>
  )
}
